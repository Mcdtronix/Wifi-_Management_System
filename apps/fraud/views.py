"""
apps/fraud/views.py
--------------------
Fraud rule configuration and alert investigation queue.
"""

from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import FraudRule, FraudAlert
from .serializers import (
    FraudRuleSerializer,
    FraudAlertListSerializer,
    FraudAlertDetailSerializer,
    FraudAlertUpdateSerializer,
)


class FraudRuleViewSet(ModelViewSet):
    """
    Fraud detection rule management.

    list:     GET    /api/fraud/rules/
    create:   POST   /api/fraud/rules/
    retrieve: GET    /api/fraud/rules/{id}/
    update:   PUT    /api/fraud/rules/{id}/
    partial:  PATCH  /api/fraud/rules/{id}/
    destroy:  DELETE /api/fraud/rules/{id}/
    toggle:   POST   /api/fraud/rules/{id}/toggle/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = FraudRuleSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ["rule_type", "name"]

    def get_queryset(self):
        qs = FraudRule.objects.filter(is_deleted=False)
        is_enabled = self.request.query_params.get("is_enabled")
        rule_type = self.request.query_params.get("rule_type")
        if is_enabled is not None:
            qs = qs.filter(is_enabled=is_enabled.lower() == "true")
        if rule_type:
            qs = qs.filter(rule_type=rule_type)
        return qs

    @action(detail=True, methods=["post"], url_path="toggle")
    def toggle(self, request, pk=None):
        """Enable or disable a fraud rule."""
        rule = self.get_object()
        rule.is_enabled = not rule.is_enabled
        rule.save(update_fields=["is_enabled", "updated_at"])
        state = "enabled" if rule.is_enabled else "disabled"
        return Response({"detail": f"Rule '{rule.name}' is now {state}."})


class FraudAlertViewSet(ReadOnlyModelViewSet):
    """
    Fraud alert investigation queue.

    list:        GET   /api/fraud/alerts/
    retrieve:    GET   /api/fraud/alerts/{id}/
    investigate: PATCH /api/fraud/alerts/{id}/investigate/
    resolve:     POST  /api/fraud/alerts/{id}/resolve/
    dismiss:     POST  /api/fraud/alerts/{id}/dismiss/
    lock_subscriber: POST /api/fraud/alerts/{id}/lock-subscriber/
    summary:     GET   /api/fraud/alerts/summary/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "severity", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            FraudAlert.objects
            .filter(is_deleted=False)
            .select_related("subscriber", "rule", "investigated_by")
        )
        alert_status = self.request.query_params.get("status")
        severity = self.request.query_params.get("severity")
        subscriber_id = self.request.query_params.get("subscriber_id")

        if alert_status:
            qs = qs.filter(status=alert_status)
        if severity:
            qs = qs.filter(severity=severity)
        if subscriber_id:
            qs = qs.filter(subscriber_id=subscriber_id)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return FraudAlertListSerializer
        return FraudAlertDetailSerializer

    @action(detail=True, methods=["patch"], url_path="investigate")
    def investigate(self, request, pk=None):
        """
        PATCH /api/fraud/alerts/{id}/investigate/
        Assign the alert to the requesting admin and add investigation notes.
        """
        alert = self.get_object()
        serializer = FraudAlertUpdateSerializer(alert, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = serializer.save(investigated_by=request.user)

        return Response(FraudAlertDetailSerializer(updated).data)

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        """
        POST /api/fraud/alerts/{id}/resolve/
        Body: { "resolution": "false_positive", "investigation_notes": "..." }
        """
        alert = self.get_object()

        if alert.status == FraudAlert.Status.RESOLVED:
            return Response(
                {"detail": "Alert is already resolved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resolution = request.data.get("resolution", "").strip()
        if not resolution:
            return Response(
                {"resolution": "A resolution type is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils import timezone
        alert.status = FraudAlert.Status.RESOLVED
        alert.resolution = resolution
        alert.investigation_notes = request.data.get("investigation_notes", "")
        alert.resolved_at = timezone.now()
        alert.investigated_by = request.user
        alert.save(update_fields=[
            "status", "resolution", "investigation_notes",
            "resolved_at", "investigated_by", "updated_at",
        ])

        return Response(
            {"detail": "Alert resolved."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="dismiss")
    def dismiss(self, request, pk=None):
        """
        POST /api/fraud/alerts/{id}/dismiss/
        Dismiss a false-positive alert without further action.
        """
        alert = self.get_object()

        reason = request.data.get("reason", "Dismissed as false positive").strip()
        alert.status = FraudAlert.Status.DISMISSED
        alert.resolution = "false_positive"
        alert.investigation_notes = reason
        alert.investigated_by = request.user
        alert.save(update_fields=[
            "status", "resolution", "investigation_notes",
            "investigated_by", "updated_at",
        ])

        return Response({"detail": "Alert dismissed."})

    @action(detail=True, methods=["post"], url_path="lock-subscriber")
    def lock_subscriber(self, request, pk=None):
        """
        POST /api/fraud/alerts/{id}/lock-subscriber/
        Immediately suspend the subscriber associated with this alert.
        """
        alert = self.get_object()
        subscriber = alert.subscriber

        if subscriber.account_status == subscriber.AccountStatus.SUSPENDED:
            return Response(
                {"detail": "Subscriber is already suspended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = f"Auto-suspended: fraud alert #{alert.id} — {alert.rule.name if alert.rule else 'Manual'}"
        subscriber.suspend(reason=reason, admin=request.user)

        alert.action_taken = f"Subscriber {subscriber.username} suspended."
        alert.save(update_fields=["action_taken", "updated_at"])

        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.SUSPEND_SUBSCRIBER,
            actor_user=request.user,
            obj=subscriber,
            description=reason,
            request=request,
        )

        return Response(
            {"detail": f"Subscriber '{subscriber.username}' has been suspended."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        GET /api/fraud/alerts/summary/
        Returns alert counts grouped by status and severity.
        """
        from django.db.models import Count
        data = {
            "by_status": list(
                self.get_queryset()
                .values("status")
                .annotate(count=Count("id"))
                .order_by("status")
            ),
            "by_severity": list(
                self.get_queryset()
                .values("severity")
                .annotate(count=Count("id"))
                .order_by("severity")
            ),
            "open_count": self.get_queryset().exclude(
                status__in=[FraudAlert.Status.RESOLVED, FraudAlert.Status.DISMISSED]
            ).count(),
        }
        return Response(data)