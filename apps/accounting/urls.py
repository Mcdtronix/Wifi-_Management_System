"""
apps/accounting/urls.py
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RadiusAccountingReceiver, RadiusAccountingViewSet, SessionViewSet

router = DefaultRouter()
router.register(r"records", RadiusAccountingViewSet, basename="accounting-records")
router.register(r"sessions", SessionViewSet, basename="accounting-sessions")

urlpatterns = [
    # FreeRADIUS posts here (rlm_rest module)
    path("radius/", RadiusAccountingReceiver.as_view(), name="radius-accounting"),
    path("", include(router.urls)),
]