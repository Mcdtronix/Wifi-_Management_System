"""
apps/bandwidth/views.py
------------------------
Bandwidth profile management for speed tiers.
"""

from rest_framework import filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.viewsets import ModelViewSet

from .models import BandwidthProfile
from .serializers import (
    BandwidthProfileListSerializer,
    BandwidthProfileDetailSerializer,
    BandwidthProfileCreateUpdateSerializer,
)


class BandwidthProfileViewSet(ModelViewSet):
    """
    Bandwidth speed tier management.

    list:     GET    /api/bandwidth/
    create:   POST   /api/bandwidth/
    retrieve: GET    /api/bandwidth/{id}/
    update:   PUT    /api/bandwidth/{id}/
    partial:  PATCH  /api/bandwidth/{id}/
    destroy:  DELETE /api/bandwidth/{id}/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["download_mbps", "upload_mbps", "tier"]
    ordering = ["download_mbps"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return BandwidthProfileCreateUpdateSerializer
        if self.action == "list":
            return BandwidthProfileListSerializer
        return BandwidthProfileDetailSerializer

    def get_queryset(self):
        qs = BandwidthProfile.objects.filter(is_deleted=False)
        tier = self.request.query_params.get("tier")
        is_active = self.request.query_params.get("is_active")
        if tier:
            qs = qs.filter(tier=tier)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def perform_destroy(self, instance):
        # Block if plans reference this profile
        if instance.plans.filter(is_deleted=False).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "This bandwidth profile is referenced by one or more plans. "
                "Remove those references before deleting."
            )
        instance.soft_delete()