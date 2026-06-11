"""
apps/subscriptions/admin.py
----------------------------
Django admin for internet plans and subscriber subscriptions.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Plan, Subscription


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0
    show_change_link = True
    readonly_fields = ("plan", "status", "activated_at", "expires_at", "amount_paid_usd", "created_by")
    fields = ("plan", "status", "activated_at", "expires_at", "amount_paid_usd", "created_by")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name", "plan_type", "duration_days", "price_usd",
        "bandwidth_profile", "quota_policy", "grace_period_hours",
        "is_active", "created_at",
    )
    list_filter = ("plan_type", "is_active")
    search_fields = ("name", "description")
    ordering = ("plan_type", "price_usd")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("bandwidth_profile", "quota_policy")

    fieldsets = (
        (_("Plan Details"), {
            "fields": ("id", "name", "plan_type", "duration_days", "price_usd", "is_active", "description"),
        }),
        (_("Network Policy"), {
            "fields": ("bandwidth_profile", "quota_policy", "grace_period_hours"),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["activate_plans", "deactivate_plans"]

    @admin.action(description=_("Activate selected plans"))
    def activate_plans(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} plan(s) activated.")

    @admin.action(description=_("Deactivate selected plans (stops new purchases)"))
    def deactivate_plans(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} plan(s) deactivated.")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "subscriber", "plan", "status_badge",
        "activated_at", "expires_at", "amount_paid_usd", "created_by",
    )
    list_filter = ("status", "plan__plan_type")
    search_fields = (
        "subscriber__username", "subscriber__full_name",
        "plan__name", "notes",
    )
    date_hierarchy = "activated_at"
    ordering = ("-activated_at",)
    readonly_fields = ("id", "created_at", "updated_at", "created_by")
    raw_id_fields = ("subscriber", "plan", "redeemed_voucher", "created_by")

    fieldsets = (
        (_("Assignment"), {
            "fields": ("id", "subscriber", "plan", "status", "redeemed_voucher"),
        }),
        (_("Dates"), {
            "fields": ("activated_at", "expires_at", "grace_ends_at"),
        }),
        (_("Billing"), {
            "fields": ("amount_paid_usd", "notes"),
        }),
        (_("Meta"), {
            "fields": ("created_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colours = {
            "active":    ("green",  "✓ Active"),
            "expired":   ("grey",   "⏰ Expired"),
            "grace":     ("blue",   "⏳ Grace"),
            "suspended": ("orange", "⏸ Suspended"),
            "cancelled": ("red",    "✗ Cancelled"),
        }
        colour, label = colours.get(obj.status, ("black", obj.status))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)
