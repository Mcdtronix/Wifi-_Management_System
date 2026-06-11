"""
apps/quota/admin.py
--------------------
Django admin for daily quota policies and per-subscriber usage records.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import DailyQuotaUsage, QuotaPolicy


@admin.register(QuotaPolicy)
class QuotaPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "name", "daily_quota_display", "warning_threshold_percent",
        "soft_limit_percent", "throttle_speed_mbps", "created_at",
    )
    search_fields = ("name", "description")
    ordering = ("daily_quota_gb",)
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (_("Policy"), {
            "fields": ("id", "name", "description"),
        }),
        (_("Quota Limits"), {
            "fields": ("daily_quota_gb", "warning_threshold_percent", "soft_limit_percent"),
            "description": _("Leave daily_quota_gb blank for unlimited. Thresholds are % of quota."),
        }),
        (_("Enforcement"), {
            "fields": ("throttle_speed_mbps",),
            "description": _("Speed after soft limit is hit. Leave blank to block access entirely."),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description=_("Daily Quota"))
    def daily_quota_display(self, obj):
        if obj.daily_quota_gb:
            return f"{obj.daily_quota_gb} GB"
        return format_html('<span style="color:green;font-weight:bold;">∞ Unlimited</span>')


@admin.register(DailyQuotaUsage)
class DailyQuotaUsageAdmin(admin.ModelAdmin):
    list_display = (
        "subscriber", "usage_date", "total_gb_display",
        "quota_limit_gb", "usage_percent_display",
        "is_exceeded", "throttled", "blocked",
    )
    list_filter = ("is_exceeded", "throttled", "blocked", "usage_date")
    search_fields = ("subscriber__username", "subscriber__full_name")
    date_hierarchy = "usage_date"
    ordering = ("-usage_date",)
    readonly_fields = (
        "id", "subscriber", "usage_date", "quota_policy",
        "upload_gb", "download_gb", "total_gb",
        "quota_limit_gb", "usage_percent", "remaining_gb",
        "is_exceeded", "warning_sent_at", "created_at", "updated_at",
    )

    fieldsets = (
        (_("Subscriber"), {"fields": ("id", "subscriber", "usage_date", "quota_policy")}),
        (_("Usage"), {
            "fields": ("upload_gb", "download_gb", "total_gb", "quota_limit_gb",
                       "usage_percent", "remaining_gb"),
        }),
        (_("State"), {"fields": ("is_exceeded", "throttled", "blocked", "warning_sent_at")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        # Usage records are created by the accounting signal handler — not manually.
        return False

    @admin.display(description=_("Total Used"))
    def total_gb_display(self, obj):
        return f"{obj.total_gb:.3f} GB"

    @admin.display(description=_("Usage %"))
    def usage_percent_display(self, obj):
        pct = obj.usage_percent
        colour = "red" if pct >= 100 else "orange" if pct >= 80 else "green"
        return format_html(
            '<span style="color:{};font-weight:bold;">{:.1f}%</span>', colour, pct
        )
