"""
apps/quota/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuotaPolicyViewSet, DailyQuotaUsageViewSet

router = DefaultRouter()
router.register(r"policies", QuotaPolicyViewSet, basename="quota-policies")
router.register(r"usage", DailyQuotaUsageViewSet, basename="quota-usage")

urlpatterns = [
    path("", include(router.urls)),
]