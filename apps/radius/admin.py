"""
apps/radius/admin.py
---------------------
Django admin for FreeRADIUS configuration and reply attributes.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import RadiusConfig, RadiusReplyAttribute


@admin.register(RadiusConfig)
class RadiusConfigAdmin(admin.ModelAdmin):
    list_display = (
        "server_host", "server_port", "accounting_port",
        "accounting_enabled", "allow_concurrent_sessions",
        "max_sessions_per_user", "created_at",
    )
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (_("Server"), {
            "fields": ("id", "server_host", "server_port", "shared_secret"),
            "description": _("⚠ The shared secret is stored in plaintext. Use environment variables in production."),
        }),
        (_("Accounting"), {
            "fields": ("accounting_enabled", "accounting_port", "interim_update_interval"),
        }),
        (_("Timeouts & Retries"), {
            "fields": ("auth_timeout_seconds", "max_retries", "session_timeout_seconds"),
        }),
        (_("Policy"), {
            "fields": ("allow_concurrent_sessions", "max_sessions_per_user"),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(RadiusReplyAttribute)
class RadiusReplyAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "name", "attribute_type", "operator",
        "value_template_excerpt", "is_reply", "is_enabled", "priority",
    )
    list_filter = ("attribute_type", "is_reply", "is_enabled")
    search_fields = ("name", "value_template", "description")
    ordering = ("priority", "name")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (_("Attribute"), {
            "fields": ("id", "name", "attribute_type", "operator", "is_reply", "is_enabled", "priority"),
        }),
        (_("Value"), {
            "fields": ("value_template", "description"),
            "description": _("Use {field} syntax e.g. {bandwidth_profile.download_bps}."),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["enable_attributes", "disable_attributes"]

    @admin.display(description=_("Value Template"))
    def value_template_excerpt(self, obj):
        return obj.value_template[:60] + "…" if len(obj.value_template) > 60 else obj.value_template

    @admin.action(description=_("Enable selected RADIUS attributes"))
    def enable_attributes(self, request, queryset):
        updated = queryset.update(is_enabled=True)
        self.message_user(request, f"{updated} attribute(s) enabled.")

    @admin.action(description=_("Disable selected RADIUS attributes"))
    def disable_attributes(self, request, queryset):
        updated = queryset.update(is_enabled=False)
        self.message_user(request, f"{updated} attribute(s) disabled.")
