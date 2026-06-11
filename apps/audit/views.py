"""
apps/audit/views.py
--------------------
Immutable audit log — read only (by design).
No create/update/delete endpoints. Writes happen internally via AuditLog.log().
"""

from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import AuditLog, AdminActivityLog
from .serializers import (
    AuditLogSerializer,
    AuditLogListSerializer,
    AdminActivityLogSerializer,
    AdminActivityLogListSerializer,
)


class AuditLogViewSet(ReadOnlyModelViewSet):
    """
    Read-only audit log — every significant event in the system.

    list:     GET /api/audit/logs/
    retrieve: GET /api/audit/logs/{id}/
    by_actor: GET /api/audit/logs/by-actor/?user_id=<uuid>
    by_object: GET /api/audit/logs/by-object/?type=subscriber&id=<uuid>
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "action", "severity"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = AuditLog.objects.select_related(
            "actor_user", "actor_subscriber", "content_type"
        )

        # Filtering
        action = self.request.query_params.get("action")
        severity = self.request.query_params.get("severity")
        actor_user_id = self.request.query_params.get("actor_user_id")
        actor_subscriber_id = self.request.query_params.get("actor_subscriber_id")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if action:
            qs = qs.filter(action=action)
        if severity:
            qs = qs.filter(severity=severity)
        if actor_user_id:
            qs = qs.filter(actor_user_id=actor_user_id)
        if actor_subscriber_id:
            qs = qs.filter(actor_subscriber_id=actor_subscriber_id)
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return AuditLogListSerializer
        return AuditLogSerializer

    @action(detail=False, methods=["get"], url_path="by-actor")
    def by_actor(self, request):
        """
        GET /api/audit/logs/by-actor/?user_id=<uuid>
        Returns all log entries for a specific admin user.
        """
        user_id = request.query_params.get("user_id")
        if not user_id:
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {"detail": "user_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = self.get_queryset().filter(actor_user_id=user_id)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(AuditLogListSerializer(page, many=True).data)
        return Response(AuditLogListSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="by-object")
    def by_object(self, request):
        """
        GET /api/audit/logs/by-object/?type=subscriber&object_id=<uuid>
        Returns all log entries that touched a specific record.
        """
        from django.contrib.contenttypes.models import ContentType
        from rest_framework import status

        model_name = request.query_params.get("type", "").lower()
        object_id = request.query_params.get("object_id")

        if not model_name or not object_id:
            return Response(
                {"detail": "'type' and 'object_id' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ct = ContentType.objects.get(model=model_name)
        except ContentType.DoesNotExist:
            return Response(
                {"detail": f"Unknown model type: {model_name}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(content_type=ct, object_id=str(object_id))
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(AuditLogListSerializer(page, many=True).data)
        return Response(AuditLogListSerializer(qs, many=True).data)


class AdminActivityLogViewSet(ReadOnlyModelViewSet):
    """
    Read-only admin activity log — what each admin has done.

    list:     GET /api/audit/admin-activity/
    retrieve: GET /api/audit/admin-activity/{id}/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "action"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = AdminActivityLog.objects.select_related("admin", "target_user")

        admin_id = self.request.query_params.get("admin_id")
        log_action = self.request.query_params.get("action")

        if admin_id:
            qs = qs.filter(admin_id=admin_id)
        if log_action:
            qs = qs.filter(action=log_action)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return AdminActivityLogListSerializer
        return AdminActivityLogSerializer