"""
apps/subscriptions/urls.py
---------------------------
URL routing for internet plans and subscriber subscriptions.

SubscriptionViewSet extends ReadOnlyModelViewSet and manually implements
`create`, so we register it with the router as-is — the router exposes
GET list/detail and any @action-decorated endpoints. The `create` action
is wired separately on the list route so POST /api/v1/subscriptions/ works.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PlanViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plans")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscriptions")

urlpatterns = [
    path("", include(router.urls)),
]