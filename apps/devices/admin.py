"""
apps/devices/admin.py
----------------------
Django admin for subscriber device management and change request workflow.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Device, DeviceChangeRequest


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "mac_address", "device_name", "subscriber", "status_badge",
        "is_primary", "first_seen_at", "last_seen_at",
    )
    list_filter = ("status", "is_primary")
    search_fields = ("mac_address", "device_name", "subscriber__username", "subscriber__full_name")
    ordering = ("-first_seen_at",)
    readonly_fields = ("id", "first_seen_at", "last_seen_at", "created_at", "updated_at")
    raw_id_fields = ("subscriber", "registered_by")

    fieldsets = (
        (_("Device"), {"fields": ("id", "mac_address", "device_name")}),
        (_("Subscriber"), {"fields": ("subscriber", "registered_by")}),
        (_("Status"), {"fields": ("status", "is_primary")}),
        (_("Timestamps"), {"fields": ("first_seen_at", "last_seen_at", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["revoke_devices"]

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colours = {
            "active":   ("green",  "✓ Active"),
            "replaced": ("grey",   "↩ Replaced"),
            "revoked":  ("red",    "✗ Revoked"),
            "pending":  ("orange", "⏳ Pending"),
        }
        colour, label = colours.get(obj.status, ("black", obj.status))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)

    @admin.action(description=_("Revoke selected devices (fraud detected)"))
    def revoke_devices(self, request, queryset):
        count = 0
        for device in queryset.filter(status=Device.DeviceStatus.ACTIVE):
            device.revoke()
            count += 1
        self.message_user(request, f"{count} device(s) revoked.")


@admin.register(DeviceChangeRequest)
class DeviceChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "subscriber", "new_mac_address", "reason", "status_badge",
        "reviewed_by", "reviewed_at", "created_at",
    )
    list_filter = ("status", "reason")
    search_fields = (
        "subscriber__username", "subscriber__full_name",
        "new_mac_address", "new_device_name",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "reviewed_at", "created_at", "updated_at")
    raw_id_fields = ("subscriber", "old_device", "reviewed_by")

    fieldsets = (
        (_("Request"), {
            "fields": ("id", "subscriber", "old_device", "new_mac_address", "new_device_name", "reason", "reason_detail"),
        }),
        (_("Review"), {
            "fields": ("status", "reviewed_by", "reviewed_at", "rejection_reason"),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["approve_requests", "reject_requests"]

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colours = {
            "pending":  ("orange", "⏳ Pending"),
            "approved": ("green",  "✓ Approved"),
            "rejected": ("red",    "✗ Rejected"),
        }
        colour, label = colours.get(obj.status, ("black", obj.status))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)

    @admin.action(description=_("Approve selected device change requests"))
    def approve_requests(self, request, queryset):
        count = 0
        for req in queryset.filter(status=DeviceChangeRequest.RequestStatus.PENDING):
            req.approve(admin=request.user)
            count += 1
        self.message_user(request, f"{count} request(s) approved and devices swapped.")

    @admin.action(description=_("Reject selected device change requests"))
    def reject_requests(self, request, queryset):
        count = 0
        for req in queryset.filter(status=DeviceChangeRequest.RequestStatus.PENDING):
            req.reject(admin=request.user, reason="Rejected via bulk admin action.")
            count += 1
        self.message_user(request, f"{count} request(s) rejected.")
