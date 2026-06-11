"""
apps/devices/views.py
----------------------
MAC address device binding and device change request management.
"""

from django.db import transaction
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin

from .models import Device, DeviceChangeRequest
from .serializers import (
    DeviceListSerializer,
    DeviceDetailSerializer,
    DeviceCreateSerializer,
    DeviceUpdateSerializer,
    DeviceChangeRequestListSerializer,
    DeviceChangeRequestDetailSerializer,
    DeviceChangeRequestCreateSerializer,
    DeviceChangeRequestApprovalSerializer,
)


class DeviceViewSet(ModelViewSet):
    """
    Device registration and MAC binding management.

    list:       GET    /api/devices/
    create:     POST   /api/devices/
    retrieve:   GET    /api/devices/{id}/
    update:     PUT    /api/devices/{id}/
    partial:    PATCH  /api/devices/{id}/
    destroy:    DELETE /api/devices/{id}/
    revoke:     POST   /api/devices/{id}/revoke/
    lookup_mac: GET    /api/devices/lookup/?mac=AA:BB:CC:DD:EE:FF
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["mac_address", "device_name", "subscriber__username", "subscriber__full_name"]
    ordering_fields = ["first_seen_at", "last_seen_at", "mac_address"]
    ordering = ["-first_seen_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return DeviceCreateSerializer
        if self.action in ("update", "partial_update"):
            return DeviceUpdateSerializer
        if self.action == "list":
            return DeviceListSerializer
        return DeviceDetailSerializer

    def get_queryset(self):
        qs = (
            Device.objects
            .filter(is_deleted=False)
            .select_related("subscriber", "registered_by")
        )

        subscriber_id = self.request.query_params.get("subscriber_id")
        device_status = self.request.query_params.get("status")
        is_primary = self.request.query_params.get("is_primary")

        if subscriber_id:
            qs = qs.filter(subscriber_id=subscriber_id)
        if device_status:
            qs = qs.filter(status=device_status)
        if is_primary is not None:
            qs = qs.filter(is_primary=is_primary.lower() == "true")

        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        subscriber = serializer.validated_data["subscriber"]

        # Deactivate any existing primary device for this subscriber
        Device.objects.filter(
            subscriber=subscriber,
            is_primary=True,
            status=Device.DeviceStatus.ACTIVE,
        ).update(is_primary=False, status=Device.DeviceStatus.REPLACED)

        device = serializer.save(registered_by=self.request.user)

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.REGISTER_DEVICE,
            actor_user=self.request.user,
            obj=device,
            description=f"Device {device.mac_address} registered for {subscriber.username}.",
            request=self.request,
        )

    def perform_destroy(self, instance):
        instance.revoke(reason="Manually removed by admin")

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        """
        POST /api/devices/{id}/revoke/
        Immediately revoke device access (fraud or abuse).
        Body: { "reason": "Credential sharing detected" }
        """
        device = self.get_object()

        if device.status == Device.DeviceStatus.REVOKED:
            return Response(
                {"detail": "Device is already revoked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "Revoked by administrator").strip()
        if not reason:
            return Response(
                {"reason": "A revocation reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.revoke(reason=reason)

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.REVOKE_DEVICE,
            actor_user=request.user,
            obj=device,
            description=f"Device {device.mac_address} revoked. Reason: {reason}",
            request=request,
        )

        return Response(
            {"detail": f"Device {device.mac_address} has been revoked."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="lookup")
    def lookup_mac(self, request):
        """
        GET /api/devices/lookup/?mac=AA:BB:CC:DD:EE:FF
        Quick MAC address lookup — used by RADIUS auth handler.
        Returns the device and its subscriber if found.
        """
        mac = request.query_params.get("mac", "").strip().upper().replace("-", ":")

        if not mac:
            return Response(
                {"detail": "Query parameter 'mac' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device = (
            Device.objects
            .filter(mac_address=mac, status=Device.DeviceStatus.ACTIVE, is_primary=True)
            .select_related("subscriber")
            .first()
        )

        if not device:
            return Response(
                {"detail": "No active device found for this MAC address."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(DeviceDetailSerializer(device).data)


# ---------------------------------------------------------------------------
# Device Change Requests
# ---------------------------------------------------------------------------

class DeviceChangeRequestViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    """
    Device change request review queue.

    list:     GET  /api/devices/change-requests/
    retrieve: GET  /api/devices/change-requests/{id}/
    approve:  POST /api/devices/change-requests/{id}/approve/
    reject:   POST /api/devices/change-requests/{id}/reject/

    Subscribers submit change requests via the captive portal (separate view).
    Admins review and approve/reject here.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            DeviceChangeRequest.objects
            .filter(is_deleted=False)
            .select_related("subscriber", "old_device", "reviewed_by")
        )

        req_status = self.request.query_params.get("status")
        subscriber_id = self.request.query_params.get("subscriber_id")

        if req_status:
            qs = qs.filter(status=req_status)
        if subscriber_id:
            qs = qs.filter(subscriber_id=subscriber_id)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DeviceChangeRequestListSerializer
        return DeviceChangeRequestDetailSerializer

    @action(detail=True, methods=["post"], url_path="approve")
    @transaction.atomic
    def approve(self, request, pk=None):
        """
        POST /api/devices/change-requests/{id}/approve/
        Deactivates the old device, registers the new MAC.
        """
        change_request = self.get_object()

        if change_request.status != DeviceChangeRequest.RequestStatus.PENDING:
            return Response(
                {"detail": f"This request has already been {change_request.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_device = change_request.approve(admin=request.user)

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.APPROVE_DEVICE_CHANGE,
            actor_user=request.user,
            obj=change_request,
            description=(
                f"Device change approved for {change_request.subscriber.username}. "
                f"New device: {new_device.mac_address}"
            ),
            request=request,
        )

        # Trigger WhatsApp notification
        from apps.notifications.tasks import send_notification_async
        send_notification_async.delay(
            event_type="device_change_approved",
            subscriber_id=str(change_request.subscriber_id),
        )

        return Response(
            {
                "detail": "Device change request approved.",
                "new_device_id": str(new_device.id),
                "new_mac_address": new_device.mac_address,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        """
        POST /api/devices/change-requests/{id}/reject/
        Body: { "reason": "Insufficient proof of ownership" }
        """
        change_request = self.get_object()

        if change_request.status != DeviceChangeRequest.RequestStatus.PENDING:
            return Response(
                {"detail": f"This request has already been {change_request.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"reason": "A rejection reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        change_request.reject(admin=request.user, reason=reason)

        return Response(
            {"detail": "Device change request rejected."},
            status=status.HTTP_200_OK,
        )


class SubscriberDeviceChangeRequestView(GenericViewSet, ListModelMixin):
    """
    Captive-portal-facing endpoint for subscribers to submit device change requests.

    create: POST /api/portal/device-change-requests/
    list:   GET  /api/portal/device-change-requests/   (own requests only)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeviceChangeRequestCreateSerializer

    def get_queryset(self):
        # Subscribers only see their own requests
        return DeviceChangeRequest.objects.filter(
            subscriber=self.request.user,
            is_deleted=False,
        )

    def create(self, request, *args, **kwargs):
        """Submit a new device change request from the portal."""
        subscriber = request.user  # Set by portal session auth

        # Block duplicate pending requests
        if DeviceChangeRequest.objects.filter(
            subscriber=subscriber,
            status=DeviceChangeRequest.RequestStatus.PENDING,
        ).exists():
            return Response(
                {"detail": "You already have a pending device change request under review."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DeviceChangeRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_device = (
            Device.objects
            .filter(subscriber=subscriber, is_primary=True, status=Device.DeviceStatus.ACTIVE)
            .first()
        )

        change_request = DeviceChangeRequest.objects.create(
            subscriber=subscriber,
            old_device=old_device,
            **serializer.validated_data,
        )

        return Response(
            DeviceChangeRequestDetailSerializer(change_request).data,
            status=status.HTTP_201_CREATED,
        )