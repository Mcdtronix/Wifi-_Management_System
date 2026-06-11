"""
apps/subscriptions/views.py
----------------------------
Plan management and subscriber subscription lifecycle.
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import Plan, Subscription
from .serializers import (
    PlanListSerializer,
    PlanDetailSerializer,
    PlanCreateUpdateSerializer,
    SubscriptionListSerializer,
    SubscriptionDetailSerializer,
    SubscriptionCreateSerializer,
    SubscriptionRenewalSerializer,
)


class PlanViewSet(ModelViewSet):
    """
    Internet plan management.

    list:     GET    /api/plans/
    create:   POST   /api/plans/
    retrieve: GET    /api/plans/{id}/
    update:   PUT    /api/plans/{id}/
    partial:  PATCH  /api/plans/{id}/
    destroy:  DELETE /api/plans/{id}/
    activate: POST   /api/plans/{id}/activate/
    deactivate: POST /api/plans/{id}/deactivate/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["price_usd", "duration_days", "plan_type"]
    ordering = ["plan_type", "price_usd"]

    def get_queryset(self):
        qs = Plan.objects.filter(is_deleted=False).select_related(
            "bandwidth_profile", "quota_policy"
        )
        plan_type = self.request.query_params.get("type")
        is_active = self.request.query_params.get("is_active")

        if plan_type:
            qs = qs.filter(plan_type=plan_type)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PlanCreateUpdateSerializer
        if self.action == "list":
            return PlanListSerializer
        return PlanDetailSerializer

    def perform_destroy(self, instance):
        # Block deletion if subscriptions reference this plan
        if instance.subscriptions.filter(
            status=Subscription.SubscriptionStatus.ACTIVE
        ).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "This plan has active subscriptions. "
                "Deactivate the plan first, then reassign subscribers."
            )
        instance.soft_delete()

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        plan = self.get_object()
        plan.is_active = True
        plan.save(update_fields=["is_active", "updated_at"])
        return Response({"detail": f"Plan '{plan.name}' is now active."})

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        plan = self.get_object()
        plan.is_active = False
        plan.save(update_fields=["is_active", "updated_at"])
        return Response({"detail": f"Plan '{plan.name}' has been deactivated."})


class SubscriptionViewSet(ReadOnlyModelViewSet):
    """
    Subscription history — read only.
    Subscriptions are created/renewed via dedicated action endpoints.

    list:     GET /api/subscriptions/
    retrieve: GET /api/subscriptions/{id}/
    create:   POST /api/subscriptions/           (assign plan to subscriber)
    renew:    POST /api/subscriptions/{id}/renew/
    cancel:   POST /api/subscriptions/{id}/cancel/
    expire:   POST /api/subscriptions/{id}/expire/   (admin force-expire)
    active:   GET  /api/subscriptions/active/        (active subs only)
    expiring: GET  /api/subscriptions/expiring/      (expiring in N days)
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["activated_at", "expires_at", "status"]
    ordering = ["-activated_at"]

    def get_queryset(self):
        qs = (
            Subscription.objects
            .filter(is_deleted=False)
            .select_related(
                "subscriber",
                "plan__bandwidth_profile",
                "plan__quota_policy",
                "created_by",
                "redeemed_voucher",
            )
        )

        subscriber_id = self.request.query_params.get("subscriber_id")
        sub_status = self.request.query_params.get("status")
        plan_id = self.request.query_params.get("plan_id")

        if subscriber_id:
            qs = qs.filter(subscriber_id=subscriber_id)
        if sub_status:
            qs = qs.filter(status=sub_status)
        if plan_id:
            qs = qs.filter(plan_id=plan_id)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return SubscriptionListSerializer
        return SubscriptionDetailSerializer

    # ------------------------------------------------------------------
    # Override create (not part of ReadOnlyModelViewSet — add manually)
    # ------------------------------------------------------------------

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        POST /api/subscriptions/
        Assign a plan to a subscriber and activate it.
        Body: { "subscriber": "<uuid>", "plan": "<uuid>" }
        """
        serializer = SubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscriber = serializer.validated_data["subscriber"]
        plan = serializer.validated_data["plan"]

        if not plan.is_active:
            return Response(
                {"plan": "This plan is not currently available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscriber.account_status not in (
            subscriber.AccountStatus.ACTIVE,
            subscriber.AccountStatus.PENDING,
            subscriber.AccountStatus.EXPIRED,
        ):
            return Response(
                {"subscriber": f"Cannot assign a plan to a {subscriber.account_status} account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = Subscription.create_for_subscriber(
            subscriber=subscriber,
            plan=plan,
            admin=request.user,
        )

        # Ensure subscriber account is active
        if subscriber.account_status != subscriber.AccountStatus.ACTIVE:
            subscriber.activate()

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.ASSIGN_PLAN,
            actor_user=request.user,
            obj=subscription,
            description=f"Plan '{plan.name}' assigned to {subscriber.username}.",
            request=request,
        )

        # Trigger welcome/activation notification
        from apps.notifications.tasks import send_notification_async
        send_notification_async.delay(
            event_type="subscription_activated",
            subscriber_id=str(subscriber.id),
        )

        return Response(
            SubscriptionDetailSerializer(subscription).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="renew")
    @transaction.atomic
    def renew(self, request, pk=None):
        """
        POST /api/subscriptions/{id}/renew/
        Renews the subscription using the same plan.
        Optional body: { "extend_days": 30 }
        """
        subscription = self.get_object()
        serializer = SubscriptionRenewalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        extend_days = serializer.validated_data.get("extend_days")
        plan = subscription.plan

        new_sub = Subscription.create_for_subscriber(
            subscriber=subscription.subscriber,
            plan=plan,
            admin=request.user,
        )

        if extend_days and extend_days != plan.duration_days:
            from datetime import timedelta
            new_sub.expires_at = new_sub.activated_at + timedelta(days=extend_days)
            new_sub.save(update_fields=["expires_at", "updated_at"])

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.RENEW_SUBSCRIPTION,
            actor_user=request.user,
            obj=new_sub,
            description=f"Subscription renewed for {subscription.subscriber.username}.",
            request=request,
        )

        from apps.notifications.tasks import send_notification_async
        send_notification_async.delay(
            event_type="subscription_renewed",
            subscriber_id=str(subscription.subscriber_id),
        )

        return Response(
            SubscriptionDetailSerializer(new_sub).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        POST /api/subscriptions/{id}/cancel/
        Cancels an active subscription and suspends internet access.
        """
        subscription = self.get_object()

        if subscription.status != Subscription.SubscriptionStatus.ACTIVE:
            return Response(
                {"detail": f"Cannot cancel a subscription with status '{subscription.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription.status = Subscription.SubscriptionStatus.CANCELLED
        subscription.save(update_fields=["status", "updated_at"])

        return Response(
            {"detail": "Subscription cancelled."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="expire")
    def expire(self, request, pk=None):
        """
        POST /api/subscriptions/{id}/expire/
        Force-expire a subscription (admin override for testing or edge cases).
        """
        subscription = self.get_object()
        subscription.status = Subscription.SubscriptionStatus.EXPIRED
        subscription.expires_at = timezone.now()
        subscription.save(update_fields=["status", "expires_at", "updated_at"])

        return Response(
            {"detail": "Subscription force-expired."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        """GET /api/subscriptions/active/ — all currently active subscriptions."""
        qs = self.get_queryset().filter(status=Subscription.SubscriptionStatus.ACTIVE)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(SubscriptionListSerializer(page, many=True).data)
        return Response(SubscriptionListSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="expiring")
    def expiring(self, request):
        """
        GET /api/subscriptions/expiring/?days=7
        Returns subscriptions expiring within the next N days (default 7).
        """
        from datetime import timedelta
        try:
            days = int(request.query_params.get("days", 7))
            if days < 1 or days > 90:
                raise ValueError
        except ValueError:
            return Response(
                {"days": "Must be an integer between 1 and 90."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deadline = timezone.now() + timedelta(days=days)
        qs = self.get_queryset().filter(
            status=Subscription.SubscriptionStatus.ACTIVE,
            expires_at__lte=deadline,
            expires_at__gte=timezone.now(),
        ).order_by("expires_at")

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(SubscriptionListSerializer(page, many=True).data)
        return Response(SubscriptionListSerializer(qs, many=True).data)