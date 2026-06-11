"""
apps/subscribers/admin.py
--------------------------
Django admin for hotspot subscriber (customer) accounts.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Subscriber


class SubscriptionInline(admin.TabularInline):
    model = None  # resolved below after subscriptions model is available
    extra = 0
    show_change_link = True
    readonly_fields = ("plan", "status", "activated_at", "expires_at", "amount_paid_usd")
    fields = ("plan", "status", "activated_at", "expires_at", "amount_paid_usd")
    can_delete = False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("plan")


class DeviceInline(admin.TabularInline):
    model = None  # resolved below
    extra = 0
    show_change_link = True
    readonly_fields = ("mac_address", "device_name", "status", "is_primary", "first_seen_at")
    fields = ("mac_address", "device_name", "status", "is_primary", "first_seen_at")
    can_delete = False


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "username", "phone_number", "email",
        "status_badge", "created_by", "created_at",
    )
    list_filter = ("account_status",)
    search_fields = ("full_name", "username", "phone_number", "email", "national_id")
    ordering = ("full_name",)
    readonly_fields = ("id", "created_at", "updated_at", "created_by")

    fieldsets = (
        (_("Identity"), {
            "fields": ("id", "full_name", "username", "phone_number", "email", "national_id"),
        }),
        (_("Account Status"), {
            "fields": ("account_status", "suspension_reason"),
        }),
        (_("RADIUS"), {
            "fields": ("radius_password",),
            "description": _("Never edit the password directly. Use set_radius_password()."),
        }),
        (_("Meta"), {
            "fields": ("created_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["activate_accounts", "suspend_accounts"]

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colours = {
            "active":    ("green",  "✓ Active"),
            "suspended": ("orange", "⏸ Suspended"),
            "expired":   ("grey",   "⏰ Expired"),
            "pending":   ("blue",   "⏳ Pending"),
            "banned":    ("red",    "✗ Banned"),
        }
        colour, label = colours.get(obj.account_status, ("black", obj.account_status))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)

    @admin.action(description=_("Activate selected subscriber accounts"))
    def activate_accounts(self, request, queryset):
        for sub in queryset:
            sub.activate()
        self.message_user(request, f"{queryset.count()} subscriber(s) activated.")

    @admin.action(description=_("Suspend selected subscriber accounts"))
    def suspend_accounts(self, request, queryset):
        for sub in queryset:
            sub.suspend(reason="Bulk admin action", admin=request.user)
        self.message_user(request, f"{queryset.count()} subscriber(s) suspended.")

    def get_inline_instances(self, request, obj=None):
        """Lazy-load inlines to avoid circular import at module load time."""
        if obj is None:
            return []
        from apps.subscriptions.models import Subscription
        from apps.devices.models import Device

        class SubscriptionInlineResolved(SubscriptionInline):
            model = Subscription

        class DeviceInlineResolved(DeviceInline):
            model = Device

        return [
            SubscriptionInlineResolved(self.model, self.admin_site),
            DeviceInlineResolved(self.model, self.admin_site),
        ]
