"""
apps/captive_portal/admin.py
-----------------------------
Django admin for captive portal configuration and active portal sessions.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import PortalConfig, PortalSession


@admin.register(PortalConfig)
class PortalConfigAdmin(admin.ModelAdmin):
    list_display = (
        "site_name", "site_url", "primary_color_preview",
        "session_timeout_minutes", "terms_version", "created_at",
    )
    search_fields = ("site_name", "site_url")
    readonly_fields = ("id", "primary_color_preview", "secondary_color_preview", "created_at", "updated_at")

    fieldsets = (
        (_("Branding"), {
            "fields": ("id", "site_name", "site_url", "logo_url",
                       "header_text", "footer_text",
                       "primary_color", "secondary_color",
                       "primary_color_preview", "secondary_color_preview"),
        }),
        (_("Session Settings"), {
            "fields": ("session_timeout_minutes", "allow_remember_me"),
        }),
        (_("Registration"), {
            "fields": ("require_email", "require_phone"),
        }),
        (_("Terms & Conditions"), {
            "fields": ("show_terms", "terms_version", "terms_text"),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description=_("Primary Colour"))
    def primary_color_preview(self, obj):
        return format_html(
            '<span style="display:inline-block;width:20px;height:20px;'
            'background:{0};border-radius:50%;vertical-align:middle;margin-right:6px;"></span>{0}',
            obj.primary_color,
        )

    @admin.display(description=_("Secondary Colour"))
    def secondary_color_preview(self, obj):
        return format_html(
            '<span style="display:inline-block;width:20px;height:20px;'
            'background:{0};border-radius:50%;vertical-align:middle;margin-right:6px;"></span>{0}',
            obj.secondary_color,
        )


@admin.register(PortalSession)
class PortalSessionAdmin(admin.ModelAdmin):
    list_display = (
        "subscriber", "ip_address", "mac_address",
        "is_active", "logged_in_at", "last_activity_at", "logout_reason",
    )
    list_filter = ("is_active",)
    search_fields = (
        "subscriber__username", "subscriber__full_name",
        "ip_address", "mac_address", "session_key",
    )
    date_hierarchy = "logged_in_at"
    ordering = ("-logged_in_at",)
    readonly_fields = (
        "id", "session_key", "logged_in_at", "last_activity_at",
        "created_at", "updated_at",
    )
    raw_id_fields = ("subscriber",)

    fieldsets = (
        (_("Session"), {
            "fields": ("id", "subscriber", "session_key", "is_active"),
        }),
        (_("Network"), {
            "fields": ("ip_address", "mac_address", "user_agent"),
        }),
        (_("Lifecycle"), {
            "fields": ("logged_in_at", "last_activity_at", "logged_out_at", "logout_reason"),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False  # Created by portal auth flow only

    actions = ["force_logout"]

    @admin.action(description=_("Force logout selected portal sessions"))
    def force_logout(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(is_active=True).update(
            is_active=False,
            logged_out_at=timezone.now(),
            logout_reason="admin_force_logout",
        )
        self.message_user(request, f"{updated} session(s) force-logged out.")
