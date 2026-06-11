"""
apps/notifications/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationTemplateViewSet,
    NotificationLogViewSet,
    BulkNotificationView,
    NotificationPreferenceViewSet,
)

router = DefaultRouter()
router.register(r"templates", NotificationTemplateViewSet, basename="notification-templates")
router.register(r"log", NotificationLogViewSet, basename="notification-log")
router.register(r"preferences", NotificationPreferenceViewSet, basename="notification-preferences")

urlpatterns = [
    path("bulk/", BulkNotificationView.as_view(), name="notification-bulk"),
    path("", include(router.urls)),
]