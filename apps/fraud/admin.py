"""
apps/fraud/admin.py
--------------------
Django admin for fraud detection rules and alert case management.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import FraudAlert, FraudRule


@admin.register(FraudRule)
class FraudRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name", "rule_type", "severity_badge", "is_enabled",
        "threshold_value", "time_window_minutes",
        "auto_trigger_action", "require_admin_review",
    )
    list_filter = ("rule_type", "is_enabled", "severity", "auto_trigger_action")
    search_fields = ("name", "description")
    ordering = ("severity", "name")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (_("Rule"), {
            "fields": ("id", "name", "rule_type", "description", "is_enabled"),
        }),
        (_("Detection"), {
            "fields": ("severity", "threshold_value", "time_window_minutes"),
        }),
        (_("Response"), {
            "fields": ("auto_trigger_action", "require_admin_review"),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["enable_rules", "disable_rules"]

    @admin.display(description=_("Severity"))
    def severity_badge(self, obj):
        colours = {1: ("blue", "Low"), 2: ("orange", "Medium"), 3: ("red", "High"), 4: ("darkred", "Critical")}
        colour, label = colours.get(obj.severity, ("black", str(obj.severity)))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)

    @admin.action(description=_("Enable selected fraud rules"))
    def enable_rules(self, request, queryset):
        updated = queryset.update(is_enabled=True)
        self.message_user(request, f"{updated} rule(s) enabled.")

    @admin.action(description=_("Disable selected fraud rules"))
    def disable_rules(self, request, queryset):
        updated = queryset.update(is_enabled=False)
        self.message_user(request, f"{updated} rule(s) disabled.")


@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display = (
        "subscriber", "rule", "severity_badge", "status_badge",
        "investigated_by", "resolved_at", "action_taken", "created_at",
    )
    list_filter = ("status", "severity", "rule__rule_type")
    search_fields = (
        "subscriber__username", "subscriber__full_name",
        "description", "investigation_notes",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("id", "subscriber", "rule", "severity", "evidence",
                       "description", "created_at", "updated_at")
    raw_id_fields = ("subscriber", "investigated_by")

    fieldsets = (
        (_("Alert"), {
            "fields": ("id", "subscriber", "rule", "severity", "description"),
        }),
        (_("Evidence"), {
            "fields": ("evidence",),
            "classes": ("collapse",),
            "description": _("Raw detection data: MACs, IPs, timestamps."),
        }),
        (_("Investigation"), {
            "fields": ("status", "investigated_by", "resolution",
                       "investigation_notes", "resolved_at"),
        }),
        (_("Action Taken"), {
            "fields": ("action_taken",),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["mark_investigating", "mark_false_positive"]

    def has_add_permission(self, request):
        return False  # Alerts are created by the fraud detection engine

    @admin.display(description=_("Severity"))
    def severity_badge(self, obj):
        colours = {1: ("blue", "Low"), 2: ("orange", "Med"), 3: ("red", "High"), 4: ("darkred", "Crit")}
        colour, label = colours.get(obj.severity, ("black", "?"))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colours = {
            "open":           ("red",    "🔴 Open"),
            "investigating":  ("orange", "🔍 Investigating"),
            "resolved":       ("green",  "✓ Resolved"),
            "false_positive": ("grey",   "— False Positive"),
            "whitelisted":    ("blue",   "✓ Whitelisted"),
        }
        colour, label = colours.get(obj.status, ("black", obj.status))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)

    @admin.action(description=_("Mark selected alerts as 'Under Investigation'"))
    def mark_investigating(self, request, queryset):
        updated = queryset.filter(status=FraudAlert.Status.OPEN).update(
            status=FraudAlert.Status.INVESTIGATING,
            investigated_by=request.user,
        )
        self.message_user(request, f"{updated} alert(s) marked as investigating.")

    @admin.action(description=_("Mark selected alerts as False Positive"))
    def mark_false_positive(self, request, queryset):
        updated = queryset.update(status=FraudAlert.Status.FALSE_POSITIVE)
        self.message_user(request, f"{updated} alert(s) marked as false positive.")
