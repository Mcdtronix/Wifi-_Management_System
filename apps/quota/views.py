"""
apps/quota/views.py
--------------------
Daily quota policy management and live usage monitoring.
"""

from django.utils import timezone
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import QuotaPolicy, DailyQuotaUsage
from .serializers import (
    QuotaPolicySerializer,
    DailyQuotaUsageSerializer,
    DailyQuotaUsageListSerializer,
)


class QuotaPolicyViewSet(ModelViewSet):
    """
    Quota policy CRUD.

    list:     GET    /api/quota/policies/
    create:   POST   /api/quota/policies/
    retrieve: GET    /api/quota/policies/{id}/
    update:   PUT    /api/quota/policies/{id}/
    partial:  PATCH  /api/quota/policies/{id}/
    destroy:  DELETE /api/quota/policies/{id}/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = QuotaPolicySerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ["daily_quota_gb"]

    def get_queryset(self):
        qs = QuotaPolicy.objects.filter(is_deleted=False)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def perform_destroy(self, instance):
        if instance.plans.filter(is_deleted=False).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "This quota policy is referenced by one or more plans. "
                "Remove those plan references before deleting."
            )
        instance.soft_delete()


class DailyQuotaUsageViewSet(ReadOnlyModelViewSet):
    """
    Live daily quota usage — read only.

    list:     GET /api/quota/usage/
    retrieve: GET /api/quota/usage/{id}/
    today:    GET /api/quota/usage/today/          (all subscribers' usage today)
    exceeded: GET /api/quota/usage/exceeded/       (subscribers who've hit limit today)
    reset:    POST /api/quota/usage/{id}/reset/    (admin force-reset)
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date", "bytes_used"]
    ordering = ["-date"]

    def get_queryset(self):
        qs = DailyQuotaUsage.objects.select_related("subscriber")
        subscriber_id = self.request.query_params.get("subscriber_id")
        usage_date = self.request.query_params.get("date")
        exceeded = self.request.query_params.get("exceeded")

        if subscriber_id:
            qs = qs.filter(subscriber_id=subscriber_id)
        if usage_date:
            qs = qs.filter(date=usage_date)
        if exceeded is not None:
            qs = qs.filter(quota_exceeded=exceeded.lower() == "true")

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DailyQuotaUsageListSerializer
        return DailyQuotaUsageSerializer

    @action(detail=False, methods=["get"], url_path="today")
    def today(self, request):
        """All subscriber usages for today."""
        qs = self.get_queryset().filter(date=timezone.localdate())
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                DailyQuotaUsageListSerializer(page, many=True).data
            )
        return Response(DailyQuotaUsageListSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="exceeded")
    def exceeded(self, request):
        """Subscribers who've hit their daily quota today."""
        qs = self.get_queryset().filter(
            date=timezone.localdate(),
            quota_exceeded=True,
        )
        return Response(DailyQuotaUsageListSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="reset")
    def reset(self, request, pk=None):
        """
        POST /api/quota/usage/{id}/reset/
        Force-reset a subscriber's quota (admin override for support cases).
        """
        usage = self.get_object()
        usage.bytes_used = 0
        usage.quota_exceeded = False
        usage.exceeded_at = None
        usage.access_restored_at = timezone.now()
        usage.save()

        return Response(
            {
                "detail": (
                    f"Quota reset for {usage.subscriber.username} on {usage.date}. "
                    f"Access restored."
                )
            },
            status=status.HTTP_200_OK,
        )