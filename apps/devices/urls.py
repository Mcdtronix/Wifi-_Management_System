"""
apps/devices/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, DeviceChangeRequestViewSet

router = DefaultRouter()
router.register(r"", DeviceViewSet, basename="devices")
router.register(r"change-requests", DeviceChangeRequestViewSet, basename="device-change-requests")

urlpatterns = [
    path("", include(router.urls)),
]