"""
apps/accounts/urls.py
----------------------
URL routing for admin authentication and user/role management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminLoginView,
    AdminLogoutView,
    AdminUserViewSet,
    RoleViewSet,
    PermissionListView,
)

router = DefaultRouter()
router.register(r"users", AdminUserViewSet, basename="admin-users")
router.register(r"roles", RoleViewSet, basename="admin-roles")
router.register(r"permissions", PermissionListView, basename="admin-permissions")

urlpatterns = [
    # Authentication
    path("auth/login/", AdminLoginView.as_view(), name="admin-login"),
    path("auth/logout/", AdminLogoutView.as_view(), name="admin-logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Admin user & role management
    path("admin/", include(router.urls)),
]