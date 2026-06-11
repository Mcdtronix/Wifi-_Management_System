"""
apps/subscribers/views.py
--------------------------
Subscriber (customer) account management.
Admins create, update, suspend, and monitor subscribers.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.core.cache import cache
import random
import hashlib
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Subscriber
from .serializers import (
    SubscriberListSerializer,
    SubscriberSummarySerializer,
    SubscriberDetailSerializer,
    SubscriberCreateSerializer,
    SubscriberUpdateSerializer,
    SubscriberResetPasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    SubscriberLoginSerializer,
)


class SubscriberViewSet(ModelViewSet):
    """
    Full CRUD for hotspot subscribers.

    list:             GET    /api/subscribers/
    create:           POST   /api/subscribers/
    retrieve:         GET    /api/subscribers/{id}/
    update:           PUT    /api/subscribers/{id}/
    partial_update:   PATCH  /api/subscribers/{id}/
    destroy:          DELETE /api/subscribers/{id}/
    suspend:          POST   /api/subscribers/{id}/suspend/
    activate:         POST   /api/subscribers/{id}/activate/
    reset_password:   POST   /api/subscribers/{id}/reset-password/
    subscription:     GET    /api/subscribers/{id}/subscription/
    usage:            GET    /api/subscribers/{id}/usage/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "username", "phone_number", "email"]
    ordering_fields = ["full_name", "created_at", "account_status"]
    ordering = ["full_name"]

    def get_serializer_class(self):
        if self.action == "create":
            return SubscriberCreateSerializer
        if self.action in ("update", "partial_update"):
            return SubscriberUpdateSerializer
        if self.action == "list":
            return SubscriberSummarySerializer
        return SubscriberDetailSerializer

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        GET /api/v1/subscribers/me/
        Returns the profile of the currently logged-in subscriber.
        """
        if getattr(request.user, "is_staff", False):
            return Response(
                {"detail": "Admins do not have a subscriber profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        from django.utils import timezone
        from django.db.models import Prefetch
        from apps.subscriptions.models import Subscription
        from apps.devices.models import Device
        from apps.quota.models import DailyQuotaUsage
        from apps.subscribers.models import Subscriber
        from .serializers import SubscriberSummarySerializer

        today = timezone.localdate()
        
        qs = Subscriber.objects.filter(pk=request.user.pk).prefetch_related(
            Prefetch(
                "subscriptions",
                queryset=Subscription.objects.filter(status=Subscription.SubscriptionStatus.ACTIVE).select_related("plan__bandwidth_profile"),
                to_attr="active_subs"
            ),
            Prefetch(
                "devices",
                queryset=Device.objects.filter(status=Device.DeviceStatus.ACTIVE),
                to_attr="active_devices"
            ),
            Prefetch(
                "daily_quota_usage",
                queryset=DailyQuotaUsage.objects.filter(usage_date=today),
                to_attr="todays_usage"
            )
        )
        
        subscriber = qs.first()
        serializer = SubscriberSummarySerializer(subscriber)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        qs = Subscriber.objects.filter(is_deleted=False).select_related("created_by")

        # Optimization for the flat list summary to prevent N+1 queries
        if self.action == "list":
            from django.utils import timezone
            from django.db.models import Prefetch
            from apps.subscriptions.models import Subscription
            from apps.devices.models import Device
            from apps.quota.models import DailyQuotaUsage

            today = timezone.localdate()
            
            qs = qs.prefetch_related(
                Prefetch(
                    "subscriptions",
                    queryset=Subscription.objects.filter(status=Subscription.SubscriptionStatus.ACTIVE).select_related("plan__bandwidth_profile"),
                    to_attr="active_subs"
                ),
                Prefetch(
                    "devices",
                    queryset=Device.objects.filter(status=Device.DeviceStatus.ACTIVE),
                    to_attr="active_devices"
                ),
                Prefetch(
                    "daily_quota_usage",
                    queryset=DailyQuotaUsage.objects.filter(usage_date=today),
                    to_attr="todays_usage"
                )
            )

        # Filtering
        account_status = self.request.query_params.get("status")
        if account_status:
            valid_statuses = [s.value for s in Subscriber.AccountStatus]
            if account_status not in valid_statuses:
                return qs.none()
            qs = qs.filter(account_status=account_status)

        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        subscriber = serializer.save(created_by=self.request.user)
        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.CREATE_SUBSCRIBER,
            actor_user=self.request.user,
            obj=subscriber,
            description=f"Subscriber '{subscriber.username}' created.",
            request=self.request,
        )

    def perform_destroy(self, instance):
        # Never hard-delete — soft delete and revoke RADIUS access
        instance.soft_delete()
        instance.account_status = Subscriber.AccountStatus.BANNED
        instance.save(update_fields=["is_deleted", "deleted_at", "account_status", "updated_at"])

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="suspend")
    def suspend(self, request, pk=None):
        """
        POST /api/subscribers/{id}/suspend/
        Body: { "reason": "Non-payment" }
        """
        subscriber = self.get_object()

        if subscriber.account_status == Subscriber.AccountStatus.SUSPENDED:
            return Response(
                {"detail": "Subscriber is already suspended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"reason": "A suspension reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscriber.suspend(reason=reason, admin=request.user)

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.SUSPEND_SUBSCRIBER,
            actor_user=request.user,
            obj=subscriber,
            description=f"Subscriber '{subscriber.username}' suspended. Reason: {reason}",
            request=request,
        )

        return Response(
            {"detail": f"Subscriber '{subscriber.username}' has been suspended."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        """
        POST /api/subscribers/{id}/activate/
        Lifts a suspension and marks the account active.
        """
        subscriber = self.get_object()

        if subscriber.account_status == Subscriber.AccountStatus.BANNED:
            return Response(
                {"detail": "Banned subscribers cannot be re-activated via this endpoint. "
                           "Contact a Super Admin."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if subscriber.account_status == Subscriber.AccountStatus.ACTIVE:
            return Response(
                {"detail": "Subscriber is already active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscriber.activate()

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.ACTIVATE_SUBSCRIBER,
            actor_user=request.user,
            obj=subscriber,
            description=f"Subscriber '{subscriber.username}' re-activated.",
            request=request,
        )

        return Response(
            {"detail": f"Subscriber '{subscriber.username}' has been activated."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        """
        POST /api/subscribers/{id}/reset-password/
        Body: { "new_password": "...", "confirm_password": "..." }
        Resets the subscriber's RADIUS authentication password.
        """
        subscriber = self.get_object()
        serializer = SubscriberResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscriber.set_radius_password(serializer.validated_data["new_password"])
        subscriber.save(update_fields=["radius_password", "updated_at"])

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.RESET_PASSWORD,
            actor_user=request.user,
            obj=subscriber,
            description=f"RADIUS password reset for subscriber '{subscriber.username}'.",
            request=request,
        )

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="subscription")
    def subscription(self, request, pk=None):
        """
        GET /api/subscribers/{id}/subscription/
        Returns the subscriber's current active subscription.
        """
        subscriber = self.get_object()
        from apps.subscriptions.models import Subscription
        from apps.subscriptions.serializers import SubscriptionDetailSerializer

        active_sub = (
            Subscription.objects
            .filter(subscriber=subscriber, status=Subscription.SubscriptionStatus.ACTIVE)
            .select_related("plan__bandwidth_profile", "plan__quota_policy", "created_by")
            .first()
        )

        if not active_sub:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(SubscriptionDetailSerializer(active_sub).data)

    @action(detail=True, methods=["get"], url_path="usage")
    def usage(self, request, pk=None):
        """
        GET /api/subscribers/{id}/usage/
        Returns today's data usage summary for the subscriber.
        """
        from django.utils import timezone
        from apps.quota.models import DailyQuotaUsage
        from apps.quota.serializers import DailyQuotaUsageSerializer

        subscriber = self.get_object()
        today = timezone.localdate()

        usage = DailyQuotaUsage.objects.filter(
            subscriber=subscriber, date=today
        ).first()

        if not usage:
            return Response(
                {"detail": "No usage recorded for today.", "bytes_used": 0},
                status=status.HTTP_200_OK,
            )

        return Response(DailyQuotaUsageSerializer(usage).data)


class SubscriberPublicAuthViewSet(ViewSet):
    """
    Public unauthenticated endpoints for subscriber auth flows.
    """
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="password-reset/request")
    def request_reset(self, request):
        """
        POST /api/v1/subscribers/auth/password-reset/request/
        Accepts username and phone_number.
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        phone_number = serializer.validated_data["phone_number"]

        try:
            subscriber = Subscriber.objects.get(username=username, is_deleted=False)
        except Subscriber.DoesNotExist:
            return Response(
                {"detail": "Subscriber not found or invalid details."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscriber.phone_number != phone_number:
            return Response(
                {"detail": "Subscriber not found or invalid details."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = f"{random.randint(100000, 999999)}"
        cache_key = f"pwd_reset_otp_{username}"
        cache.set(cache_key, otp, timeout=300)

        # Dispatch mocked SMS notification
        from apps.notifications.tasks import send_notification_async
        send_notification_async.delay(
            event_type="password_reset_otp",
            subscriber_id=str(subscriber.id),
            context={"otp": otp}
        )

        # Print to console to easily find it during testing
        print(f"\\n==========================\\n🔐 OTP FOR {username}: {otp}\\n==========================\\n")

        return Response({
            "detail": "If the details are correct, an OTP has been sent to your phone."
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="password-reset/confirm")
    def confirm_reset(self, request):
        """
        POST /api/v1/subscribers/auth/password-reset/confirm/
        Accepts username, otp, new_password, confirm_password.
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        cache_key = f"pwd_reset_otp_{username}"
        cached_otp = cache.get(cache_key)

        if not cached_otp or cached_otp != otp:
            return Response(
                {"otp": "Invalid or expired OTP code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            subscriber = Subscriber.objects.get(username=username, is_deleted=False)
        except Subscriber.DoesNotExist:
            return Response(
                {"detail": "Subscriber not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        subscriber.set_radius_password(new_password)
        subscriber.save(update_fields=["radius_password", "updated_at"])

        # Invalidate OTP
        cache.delete(cache_key)

        return Response({
            "detail": "Password has been successfully reset."
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        """
        POST /api/v1/subscribers/auth/login/
        Authenticates a subscriber and returns JWT access + refresh tokens.
        """
        serializer = SubscriberLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"].strip().lower()
        password = serializer.validated_data["password"]

        try:
            subscriber = Subscriber.objects.get(username=username, is_deleted=False)
        except Subscriber.DoesNotExist:
            return Response(
                {"detail": "No active account found with the given credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if subscriber.account_status == Subscriber.AccountStatus.BANNED:
            return Response(
                {"detail": "Account is banned. Please contact support."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Verify password (matches radius_password sha256 hash logic)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if subscriber.radius_password != hashed_password:
            return Response(
                {"detail": "No active account found with the given credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        mac_address = serializer.validated_data.get("mac_address", "").strip().upper().replace("-", ":")
        device_name = serializer.validated_data.get("device_name", "").strip()

        if mac_address:
            from apps.devices.models import Device
            # Check if subscriber has an active primary device
            active_device = Device.objects.filter(
                subscriber=subscriber,
                is_primary=True,
                status=Device.DeviceStatus.ACTIVE
            ).first()

            if not active_device:
                # First time login -> Register device automatically
                from django.db import IntegrityError
                from django.core.exceptions import ValidationError
                try:
                    Device.objects.create(
                        subscriber=subscriber,
                        mac_address=mac_address,
                        device_name=device_name or "Unknown Device",
                        is_primary=True,
                        status=Device.DeviceStatus.ACTIVE
                    )
                except IntegrityError:
                    return Response(
                        {"detail": "This MAC address is already registered to another account."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                except ValidationError:
                    # Ignore invalid MAC address format silently
                    pass
            else:
                # Subscriber has an active device, ensure it matches
                if active_device.mac_address != mac_address:
                    return Response(
                        {"detail": "This device is not registered to your account. Please submit a Device Change Request."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

        # Generate tokens and inject custom user_type
        refresh = RefreshToken.for_user(subscriber)
        refresh['user_type'] = 'subscriber'

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)