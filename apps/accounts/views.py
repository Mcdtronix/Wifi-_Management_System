"""
apps/accounts/views.py
-----------------------
Admin user and role management views.
All endpoints require JWT authentication.
Role-level actions require Super Admin or Admin level.
"""

from django.utils import timezone
from django.contrib.auth.models import Permission
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import AdminUser, Role
from .serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserCreateSerializer,
    RoleSerializer,
    PermissionSerializer,
)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class AdminLoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Authenticates an admin user and returns JWT access + refresh tokens.
    Enforces account lockout policy before issuing tokens.
    """

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "").strip().lower()

        # Pre-flight: check lockout before hitting SimpleJWT
        try:
            user = AdminUser.objects.get(email=email)
            if user.is_locked:
                remaining = (user.locked_until - timezone.now()).seconds // 60
                return Response(
                    {
                        "detail": (
                            f"Account is locked due to too many failed login attempts. "
                            f"Try again in {remaining} minute(s)."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        except AdminUser.DoesNotExist:
            pass  # Let SimpleJWT return its standard 401

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Successful login — reset failure counter and record IP
            try:
                user = AdminUser.objects.get(email=email)
                user.reset_login_failures()
                user.last_login_ip = self._get_client_ip(request)
                user.save(update_fields=["last_login_ip", "updated_at"])
            except AdminUser.DoesNotExist:
                pass
        else:
            # Failed login — increment counter
            try:
                user = AdminUser.objects.get(email=email)
                user.record_failed_login()
            except AdminUser.DoesNotExist:
                pass

        return response

    @staticmethod
    def _get_client_ip(request) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class AdminLogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklists the refresh token, effectively logging the admin out.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ---------------------------------------------------------------------------
# Admin Users
# ---------------------------------------------------------------------------

class AdminUserViewSet(ModelViewSet):
    """
    CRUD for administrator accounts.

    list:        GET  /api/admin/users/
    create:      POST /api/admin/users/
    retrieve:    GET  /api/admin/users/{id}/
    update:      PUT  /api/admin/users/{id}/
    partial:     PATCH /api/admin/users/{id}/
    destroy:     DELETE /api/admin/users/{id}/
    me:          GET  /api/admin/users/me/
    change_password: POST /api/admin/users/{id}/change-password/
    lock:        POST /api/admin/users/{id}/lock/
    unlock:      POST /api/admin/users/{id}/unlock/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = AdminUser.objects.select_related("role").order_by("full_name")

    def get_serializer_class(self):
        if self.action == "create":
            return AdminUserCreateSerializer
        if self.action in ("list",):
            return AdminUserListSerializer
        return AdminUserDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        # Filter params
        is_active = self.request.query_params.get("is_active")
        role_id = self.request.query_params.get("role_id")
        search = self.request.query_params.get("search", "").strip()

        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        if role_id:
            qs = qs.filter(role_id=role_id)
        if search:
            qs = qs.filter(full_name__icontains=search) | qs.filter(email__icontains=search)

        return qs

    def perform_create(self, serializer):
        user = serializer.save()
        # Audit: log admin creation (import inline to avoid circular)
        from apps.audit.models import AuditLog
        AuditLog.log(
            action=AuditLog.Action.ADMIN_CREATE_USER,
            actor_user=self.request.user,
            obj=user,
            description=f"Admin account created for {user.email}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        # Soft-delete; never physically remove admin accounts
        if instance == self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot delete your own account.")
        instance.soft_delete()

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """Return the currently authenticated admin's profile."""
        serializer = AdminUserDetailSerializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        """
        POST /api/admin/users/{id}/change-password/
        Body: { "old_password": "...", "new_password": "...", "confirm_password": "..." }
        """
        user = self.get_object()
        old_password = request.data.get("old_password", "")
        new_password = request.data.get("new_password", "")
        confirm_password = request.data.get("confirm_password", "")

        errors = {}

        # Only the user themselves or Super Admin can change passwords
        is_self = request.user == user
        is_super = (
            request.user.role and
            request.user.role.level == request.user.role.RoleLevel.SUPER_ADMIN
        )

        if not (is_self or is_super):
            return Response(
                {"detail": "You do not have permission to change this user's password."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if is_self and not user.check_password(old_password):
            errors["old_password"] = "Incorrect current password."

        if len(new_password) < 8:
            errors["new_password"] = "Password must be at least 8 characters."

        if new_password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if new_password == old_password:
            errors["new_password"] = "New password must differ from the current password."

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="lock")
    def lock(self, request, pk=None):
        """Manually lock an admin account."""
        user = self.get_object()
        if user == request.user:
            return Response(
                {"detail": "You cannot lock your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from datetime import timedelta
        user.locked_until = timezone.now() + timedelta(days=365)
        user.save(update_fields=["locked_until", "updated_at"])
        return Response({"detail": f"{user.full_name}'s account has been locked."})

    @action(detail=True, methods=["post"], url_path="unlock")
    def unlock(self, request, pk=None):
        """Unlock a locked admin account."""
        user = self.get_object()
        user.reset_login_failures()
        return Response({"detail": f"{user.full_name}'s account has been unlocked."})


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

class RoleViewSet(ModelViewSet):
    """
    CRUD for admin roles.

    list:     GET  /api/admin/roles/
    create:   POST /api/admin/roles/
    retrieve: GET  /api/admin/roles/{id}/
    update:   PUT  /api/admin/roles/{id}/
    destroy:  DELETE /api/admin/roles/{id}/
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = RoleSerializer
    queryset = Role.objects.prefetch_related("permissions").order_by("level")

    def perform_destroy(self, instance):
        if instance.admin_users.filter(is_deleted=False).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "This role is assigned to one or more active admin users. "
                "Reassign those users before deleting the role."
            )
        instance.soft_delete()


# ---------------------------------------------------------------------------
# Permissions (read-only reference)
# ---------------------------------------------------------------------------

class PermissionListView(ReadOnlyModelViewSet):
    """
    GET /api/admin/permissions/
    Returns all available Django permissions for use in role assignment.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = PermissionSerializer
    queryset = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label", "codename"
    )