"""
apps/vouchers/views.py
-----------------------
Voucher batch generation and individual voucher management.
"""

from django.db import transaction
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import Voucher, VoucherBatch
from .serializers import (
    VoucherBatchListSerializer,
    VoucherBatchDetailSerializer,
    VoucherBatchCreateSerializer,
    VoucherListSerializer,
    VoucherDetailSerializer,
    VoucherRedemptionSerializer,
    VoucherBulkCreateSerializer,
)


class VoucherBatchViewSet(ModelViewSet):
    """
    Voucher batch generation and management.

    list:     GET    /api/vouchers/batches/
    create:   POST   /api/vouchers/batches/          (generates batch + codes)
    retrieve: GET    /api/vouchers/batches/{id}/
    destroy:  DELETE /api/vouchers/batches/{id}/
    vouchers: GET    /api/vouchers/batches/{id}/vouchers/
    export:   GET    /api/vouchers/batches/{id}/export/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "plan__name"]
    ordering_fields = ["created_at", "quantity"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "delete", "head", "options"]  # No PUT/PATCH on batches

    def get_serializer_class(self):
        if self.action == "create":
            return VoucherBatchCreateSerializer
        if self.action == "list":
            return VoucherBatchListSerializer
        return VoucherBatchDetailSerializer

    def get_queryset(self):
        qs = VoucherBatch.objects.filter(is_deleted=False).select_related(
            "plan", "generated_by"
        )
        plan_id = self.request.query_params.get("plan_id")
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        batch = serializer.save(generated_by=self.request.user)

        # Bulk-generate voucher codes
        vouchers = [
            Voucher(batch=batch)
            for _ in range(batch.quantity)
        ]
        # Ensure uniqueness — regenerate any collisions
        created_codes = set()
        unique_vouchers = []
        for v in vouchers:
            attempts = 0
            while v.code in created_codes:
                from .models import _generate_voucher_code
                v.code = _generate_voucher_code()
                attempts += 1
                if attempts > 10:
                    break
            # Also check DB for any pre-existing code
            while Voucher.objects.filter(code=v.code).exists():
                from .models import _generate_voucher_code
                v.code = _generate_voucher_code()
            created_codes.add(v.code)
            unique_vouchers.append(v)

        Voucher.objects.bulk_create(unique_vouchers)

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.GENERATE_VOUCHERS,
            actor_user=self.request.user,
            obj=batch,
            description=f"Generated {batch.quantity} vouchers in batch '{batch.name}'.",
            request=self.request,
        )

    def perform_destroy(self, instance):
        if instance.vouchers.filter(status=Voucher.VoucherStatus.REDEEMED).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "This batch contains redeemed vouchers and cannot be deleted. "
                "Void unused codes individually if needed."
            )
        instance.soft_delete()

    @action(detail=True, methods=["get"], url_path="vouchers")
    def vouchers(self, request, pk=None):
        """
        GET /api/vouchers/batches/{id}/vouchers/?status=unused
        Lists all voucher codes within this batch.
        """
        batch = self.get_object()
        qs = batch.vouchers.all()

        voucher_status = request.query_params.get("status")
        if voucher_status:
            qs = qs.filter(status=voucher_status)

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(VoucherListSerializer(page, many=True).data)
        return Response(VoucherListSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="export")
    def export(self, request, pk=None):
        """
        GET /api/vouchers/batches/{id}/export/
        Returns all unused voucher codes as a simple JSON list for printing.
        """
        batch = self.get_object()
        codes = list(
            batch.vouchers
            .filter(status=Voucher.VoucherStatus.UNUSED)
            .values_list("code", flat=True)
            .order_by("code")
        )
        return Response(
            {
                "batch_name": batch.name,
                "plan": str(batch.plan),
                "valid_from": batch.valid_from,
                "valid_until": batch.valid_until,
                "total_unused": len(codes),
                "codes": codes,
            }
        )


class VoucherViewSet(ReadOnlyModelViewSet):
    """
    Individual voucher lookup and management.

    list:     GET  /api/vouchers/
    retrieve: GET  /api/vouchers/{id}/
    redeem:   POST /api/vouchers/redeem/      (captive portal — subscriber action)
    void:     POST /api/vouchers/{id}/void/   (admin action)
    bulk_void: POST /api/vouchers/bulk/       (admin bulk action)
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "redeemed_by__username", "batch__name"]
    ordering_fields = ["code", "redeemed_at", "status"]
    ordering = ["code"]

    def get_queryset(self):
        qs = (
            Voucher.objects
            .filter(is_deleted=False)
            .select_related("batch__plan", "redeemed_by", "voided_by")
        )

        voucher_status = self.request.query_params.get("status")
        batch_id = self.request.query_params.get("batch_id")

        if voucher_status:
            qs = qs.filter(status=voucher_status)
        if batch_id:
            qs = qs.filter(batch_id=batch_id)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return VoucherListSerializer
        return VoucherDetailSerializer

    @action(
        detail=False,
        methods=["post"],
        url_path="redeem",
        permission_classes=[IsAuthenticated],  # Subscriber auth — not admin
    )
    @transaction.atomic
    def redeem(self, request):
        """
        POST /api/vouchers/redeem/
        Body: { "voucher_code": "TGD-XXXX-XXXX" }
        Called from the captive portal when a subscriber pays via voucher.
        Validates the code, redeems it, and activates the associated plan.
        """
        serializer = VoucherRedemptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["voucher_code"].upper()

        try:
            voucher = Voucher.objects.select_related("batch__plan").get(code=code)
        except Voucher.DoesNotExist:
            return Response(
                {"voucher_code": "Voucher code not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not voucher.is_redeemable:
            return Response(
                {"voucher_code": f"This voucher is {voucher.status} and cannot be redeemed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscriber = request.user
        plan = voucher.batch.plan

        if not plan.is_active:
            return Response(
                {"detail": "The plan associated with this voucher is no longer available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Redeem voucher
        voucher.redeem(subscriber=subscriber)

        # Activate subscription
        from apps.subscriptions.models import Subscription
        subscription = Subscription.create_for_subscriber(
            subscriber=subscriber,
            plan=plan,
            voucher=voucher,
        )

        # Activate subscriber account if pending/expired
        if subscriber.account_status != subscriber.AccountStatus.ACTIVE:
            subscriber.activate()

        from apps.notifications.tasks import send_notification_async
        send_notification_async.delay(
            event_type="subscription_activated",
            subscriber_id=str(subscriber.id),
        )

        from apps.subscriptions.serializers import SubscriptionDetailSerializer
        return Response(
            {
                "detail": f"Voucher redeemed. Plan '{plan.name}' is now active.",
                "subscription": SubscriptionDetailSerializer(subscription).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="void")
    def void(self, request, pk=None):
        """
        POST /api/vouchers/{id}/void/
        Body: { "reason": "Damaged / Printing error" }
        """
        voucher = self.get_object()
        reason = request.data.get("reason", "").strip()

        if not reason:
            return Response(
                {"reason": "A void reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            voucher.void(admin=request.user, reason=reason)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"detail": f"Voucher {voucher.code} has been voided."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="bulk")
    @transaction.atomic
    def bulk(self, request):
        """
        POST /api/vouchers/bulk/
        Body: { "voucher_ids": [...], "action": "void" }
        Perform a bulk action on a list of vouchers.
        """
        serializer = VoucherBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        voucher_ids = serializer.validated_data["voucher_ids"]
        bulk_action = serializer.validated_data["action"]

        if len(voucher_ids) > 500:
            return Response(
                {"detail": "Cannot perform bulk actions on more than 500 vouchers at once."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vouchers = Voucher.objects.filter(
            id__in=voucher_ids,
            status=Voucher.VoucherStatus.UNUSED,
            is_deleted=False,
        )

        if bulk_action == "void":
            reason = request.data.get("reason", "Bulk void by administrator").strip()
            if not reason:
                return Response(
                    {"reason": "A void reason is required for bulk void."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            count = vouchers.count()
            vouchers.update(
                status=Voucher.VoucherStatus.VOIDED,
                voided_by=request.user,
                void_reason=reason,
            )
            return Response(
                {"detail": f"{count} voucher(s) have been voided."},
                status=status.HTTP_200_OK,
            )

        elif bulk_action == "export":
            codes = list(vouchers.values_list("code", flat=True))
            return Response({"codes": codes, "count": len(codes)})

        return Response(
            {"action": f"Unknown action '{bulk_action}'."},
            status=status.HTTP_400_BAD_REQUEST,
        )