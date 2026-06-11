"""
apps/bandwidth/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BandwidthProfileViewSet

router = DefaultRouter()
router.register(r"", BandwidthProfileViewSet, basename="bandwidth-profiles")

urlpatterns = [
    path("", include(router.urls)),
]