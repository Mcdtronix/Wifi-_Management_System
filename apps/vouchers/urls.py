"""
apps/vouchers/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VoucherBatchViewSet, VoucherViewSet

router = DefaultRouter()
router.register(r"batches", VoucherBatchViewSet, basename="voucher-batches")
router.register(r"", VoucherViewSet, basename="vouchers")

urlpatterns = [
    path("", include(router.urls)),
]