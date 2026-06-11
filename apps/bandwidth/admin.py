"""
apps/bandwidth/admin.py
------------------------
Django admin for bandwidth speed profiles.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import BandwidthProfile


@admin.register(BandwidthProfile)
class BandwidthProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name", "tier", "download_mbps", "upload_mbps",
        "download_bps_display", "upload_bps_display", "is_active", "created_at",
    )
    list_filter = ("tier", "is_active")
    search_fields = ("name",)
    ordering = ("download_mbps",)
    readonly_fields = ("id", "download_bps", "upload_bps", "created_at", "updated_at")

    fieldsets = (
        (_("Profile"), {
            "fields": ("id", "name", "tier", "is_active"),
        }),
        (_("Speed Limits"), {
            "fields": ("download_mbps", "upload_mbps"),
            "description": _("Upload should not exceed download. Tier speeds are fixed."),
        }),
        (_("RADIUS Attributes (computed)"), {
            "fields": ("download_bps", "upload_bps"),
            "description": _("These values are sent as WISPr-Bandwidth-Max-Down / Up to FreeRADIUS."),
            "classes": ("collapse",),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["activate_profiles", "deactivate_profiles"]

    @admin.display(description=_("Download (bps)"))
    def download_bps_display(self, obj):
        return f"{obj.download_bps:,} bps"

    @admin.display(description=_("Upload (bps)"))
    def upload_bps_display(self, obj):
        return f"{obj.upload_bps:,} bps"

    @admin.action(description=_("Activate selected profiles"))
    def activate_profiles(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} profile(s) activated.")

    @admin.action(description=_("Deactivate selected profiles"))
    def deactivate_profiles(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} profile(s) deactivated.")
