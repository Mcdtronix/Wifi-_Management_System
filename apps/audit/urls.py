"""
apps/audit/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet, AdminActivityLogViewSet

router = DefaultRouter()
router.register(r"logs", AuditLogViewSet, basename="audit-logs")
router.register(r"admin-activity", AdminActivityLogViewSet, basename="admin-activity")

urlpatterns = [
    path("", include(router.urls)),
]