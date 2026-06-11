"""
apps/accounts/admin.py
-----------------------
Django admin configuration for platform administrator accounts and roles.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import AdminUser, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "get_level_display", "permissions_count", "created_at")
    list_filter = ("level",)
    search_fields = ("name", "description")
    ordering = ("level",)
    filter_horizontal = ("permissions",)
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "name", "level", "description")}),
        (_("Permissions"), {"fields": ("permissions",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description=_("Permissions"))
    def permissions_count(self, obj):
        count = obj.permissions.count()
        return f"{count} permission{'s' if count != 1 else ''}"


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    list_display = (
        "email", "full_name", "role", "is_active", "is_staff",
        "is_locked_badge", "last_login_ip", "created_at",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "role")
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("full_name",)
    readonly_fields = ("id", "last_login_ip", "failed_login_count", "locked_until", "created_at", "updated_at")

    # Override UserAdmin fieldsets — we use email, not username
    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Personal Info"), {"fields": ("full_name", "phone_number")}),
        (_("Role & Access"), {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        (_("Groups & Permissions"), {"fields": ("groups", "user_permissions"), "classes": ("collapse",)}),
        (_("Security"), {"fields": ("last_login_ip", "failed_login_count", "locked_until")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2", "role", "is_active", "is_staff"),
        }),
    )

    @admin.display(description=_("Locked"), boolean=False)
    def is_locked_badge(self, obj):
        if obj.is_locked:
            return format_html('<span style="color:red;font-weight:bold;">🔒 Locked</span>')
        return format_html('<span style="color:green;">✓ Open</span>')
