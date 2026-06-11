"""
apps/fraud/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FraudRuleViewSet, FraudAlertViewSet

router = DefaultRouter()
router.register(r"rules", FraudRuleViewSet, basename="fraud-rules")
router.register(r"alerts", FraudAlertViewSet, basename="fraud-alerts")

urlpatterns = [
    path("", include(router.urls)),
]