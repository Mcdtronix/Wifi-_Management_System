"""
apps/notifications/views.py
----------------------------
WhatsApp notification template management and delivery log browser.
"""

from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import NotificationTemplate, Notification, NotificationPreference
from .serializers import (
    NotificationTemplateSerializer,
    NotificationListSerializer,
    NotificationDetailSerializer,
    NotificationPreferenceSerializer,
    BulkNotificationSerializer,
)


class NotificationTemplateViewSet(ModelViewSet):
    """
    Manage WhatsApp message templates.

    list:     GET    /api/notifications/templates/
    create:   POST   /api/notifications/templates/
    retrieve: GET    /api/notifications/templates/{id}/
    update:   PUT    /api/notifications/templates/{id}/
    partial:  PATCH  /api/notifications/templates/{id}/
    destroy:  DELETE /api/notifications/templates/{id}/
    preview:  POST   /api/notifications/templates/{id}/preview/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = NotificationTemplateSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ["event_type", "name"]

    def get_queryset(self):
        qs = NotificationTemplate.objects.filter(is_deleted=False)
        event_type = self.request.query_params.get("event_type")
        is_active = self.request.query_params.get("is_active")
        if event_type:
            qs = qs.filter(event_type=event_type)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, pk=None):
        """
        POST /api/notifications/templates/{id}/preview/
        Body: { "context_data": { "subscriber_name": "John", ... } }
        Returns the rendered template body with sample data substituted.
        """
        template = self.get_object()
        context_data = request.data.get("context_data", {})

        if not isinstance(context_data, dict):
            return Response(
                {"context_data": "Must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rendered_body = template.body.format(**context_data)
        except KeyError as e:
            return Response(
                {"detail": f"Missing template variable: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "template_name": template.name,
                "event_type": template.event_type,
                "rendered_body": rendered_body,
                "context_data": context_data,
            }
        )


class NotificationLogViewSet(ReadOnlyModelViewSet):
    """
    Read-only notification delivery log.

    list:     GET /api/notifications/log/
    retrieve: GET /api/notifications/log/{id}/
    retry:    POST /api/notifications/log/{id}/retry/
    stats:    GET  /api/notifications/log/stats/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["sent_at", "created_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Notification.objects.filter(is_deleted=False).select_related(
            "subscriber", "template"
        )
        sub_id = self.request.query_params.get("subscriber_id")
        notif_status = self.request.query_params.get("status")
        event_type = self.request.query_params.get("event_type")

        if sub_id:
            qs = qs.filter(subscriber_id=sub_id)
        if notif_status:
            qs = qs.filter(status=notif_status)
        if event_type:
            qs = qs.filter(event_type=event_type)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return NotificationListSerializer
        return NotificationDetailSerializer

    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request, pk=None):
        """
        POST /api/notifications/log/{id}/retry/
        Re-queues a failed notification for delivery.
        """
        notification = self.get_object()

        if notification.status not in ("failed", "pending"):
            return Response(
                {"detail": f"Only failed or pending notifications can be retried. "
                           f"Current status: {notification.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import send_notification_async
        send_notification_async.delay(
            event_type=notification.event_type,
            subscriber_id=str(notification.subscriber_id),
            notification_id=str(notification.id),
        )

        return Response(
            {"detail": "Notification queued for retry."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """
        GET /api/notifications/log/stats/
        Returns delivery statistics by status and channel.
        """
        from django.db.models import Count
        stats = (
            self.get_queryset()
            .values("status", "channel")
            .annotate(count=Count("id"))
            .order_by("status", "channel")
        )
        return Response(list(stats))


class BulkNotificationView(APIView):
    """
    POST /api/notifications/bulk/
    Send a notification to a filtered group of subscribers.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = BulkNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event_type = serializer.validated_data["event_type"]
        subscriber_filter = serializer.validated_data.get("subscriber_filter", {})

        from apps.subscribers.models import Subscriber
        qs = Subscriber.objects.filter(
            account_status=Subscriber.AccountStatus.ACTIVE,
            is_deleted=False,
        )

        if subscriber_filter:
            try:
                qs = qs.filter(**subscriber_filter)
            except Exception:
                return Response(
                    {"subscriber_filter": "Invalid filter parameters."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if qs.count() > 5000:
            return Response(
                {"detail": "Bulk notifications are limited to 5,000 subscribers at once."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import send_notification_async
        count = 0
        for subscriber in qs.only("id"):
            send_notification_async.delay(
                event_type=event_type,
                subscriber_id=str(subscriber.id),
                context_data=serializer.validated_data.get("context_data", {}),
            )
            count += 1

        return Response(
            {"detail": f"Bulk notification queued for {count} subscriber(s)."},
            status=status.HTTP_202_ACCEPTED,
        )


class NotificationPreferenceViewSet(ReadOnlyModelViewSet):
    """
    GET  /api/notifications/preferences/
    GET  /api/notifications/preferences/{id}/
    update: PATCH /api/notifications/preferences/{id}/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = NotificationPreferenceSerializer

    def get_queryset(self):
        return NotificationPreference.objects.filter(
            is_deleted=False
        ).select_related("subscriber")

    def partial_update(self, request, *args, **kwargs):
        preference = self.get_object()
        serializer = NotificationPreferenceSerializer(
            preference, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)