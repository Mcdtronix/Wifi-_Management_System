"""
apps/reporting/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardView,
    RevenueSummaryViewSet,
    SubscriberReportViewSet,
    BandwidthUsageReportView,
)

router = DefaultRouter()
router.register(r"revenue", RevenueSummaryViewSet, basename="revenue-summary")
router.register(r"subscriber-reports", SubscriberReportViewSet, basename="subscriber-reports")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="reporting-dashboard"),
    path("bandwidth/", BandwidthUsageReportView.as_view(), name="reporting-bandwidth"),
    path("", include(router.urls)),
]