"""
apps/subscribers/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriberViewSet, SubscriberPublicAuthViewSet

router = DefaultRouter()
router.register(r"auth", SubscriberPublicAuthViewSet, basename="subscriber-auth")
router.register(r"", SubscriberViewSet, basename="subscribers")

urlpatterns = [
    path("", include(router.urls)),
]