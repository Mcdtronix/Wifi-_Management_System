"""
apps/notifications/admin.py
----------------------------
Django admin for WhatsApp notification templates, delivery log, and subscriber preferences.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Notification, NotificationPreference, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name", "event_type", "channel", "is_active",
        "variables_preview", "created_at",
    )
    list_filter = ("event_type", "channel", "is_active")
    search_fields = ("name", "body", "event_type")
    ordering = ("event_type", "name")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (_("Template"), {
            "fields": ("id", "name", "event_type", "channel", "is_active"),
        }),
        (_("Content"), {
            "fields": ("body",),
            "description": _("Use {variable_name} placeholders. Preview via API."),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description=_("Variables"))
    def variables_preview(self, obj):
        import re
        variables = re.findall(r"\{(\w+)\}", obj.body)
        if variables:
            return ", ".join(f"{{{v}}}" for v in sorted(set(variables)))
        return format_html('<span style="color:grey;">none</span>')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "subscriber", "event_type", "channel", "status_badge",
        "sent_at", "retry_count", "created_at",
    )
    list_filter = ("status", "channel", "event_type")
    search_fields = ("subscriber__username", "subscriber__full_name", "event_type")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("id", "subscriber", "template", "event_type", "channel",
                       "recipient", "subject", "body", "status", "sent_at",
                       "delivered_at", "external_id", "retry_count",
                       "error_message", "context_data", "created_at", "updated_at")

    fieldsets = (
        (_('Notification'), {
            'fields': ('id', 'subscriber', 'template', 'event_type', 'channel', 'recipient'),
        }),
        (_('Content'), {
            'fields': ('subject', 'body'),
        }),
        (_('Delivery'), {
            'fields': ('status', 'sent_at', 'delivered_at', 'external_id', 'retry_count', 'error_message'),
        }),
        (_('Context'), {
            'fields': ('context_data',),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def has_add_permission(self, request):
        return False  # Notifications are created by tasks/signals, not manually

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colours = {
            "pending": ("blue",   "⏳ Pending"),
            "sent":    ("green",  "✓ Sent"),
            "failed":  ("red",    "✗ Failed"),
            "skipped": ("grey",   "— Skipped"),
        }
        colour, label = colours.get(obj.status, ("black", obj.status))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "subscriber", "receive_whatsapp", "receive_sms", "receive_email",
        "receive_quota_warnings", "receive_expiry_warnings", "updated_at",
    )
    list_filter = ("receive_whatsapp", "receive_email")
    search_fields = ("subscriber__username", "subscriber__full_name")
    ordering = ("subscriber__full_name",)
    readonly_fields = ("id", "subscriber", "created_at", "updated_at")
    raw_id_fields = ("subscriber",)

    fieldsets = (
        (_('Subscriber'), {'fields': ('id', 'subscriber')}),
        (_('Channels'), {'fields': ('receive_whatsapp', 'receive_sms', 'receive_email')}),
        (_('Notification Types'), {
            'fields': ('receive_quota_warnings', 'receive_expiry_warnings',
                       'receive_security_alerts'),
        }),
        (_('Quiet Hours'), {
            'fields': ('quiet_hours_start', 'quiet_hours_end'),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
