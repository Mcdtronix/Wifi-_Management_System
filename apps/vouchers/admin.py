"""
apps/vouchers/admin.py
-----------------------
Django admin for prepaid voucher batches and individual voucher codes.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Voucher, VoucherBatch


class VoucherInline(admin.TabularInline):
    model = Voucher
    extra = 0
    show_change_link = True
    readonly_fields = ("code", "status", "redeemed_by", "redeemed_at")
    fields = ("code", "status", "redeemed_by", "redeemed_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("redeemed_by")


@admin.register(VoucherBatch)
class VoucherBatchAdmin(admin.ModelAdmin):
    list_display = (
        "name", "plan", "quantity",
        "available_count", "redeemed_count", "voided_count",
        "valid_from", "valid_until", "generated_by", "created_at",
    )
    list_filter = ("plan",)
    search_fields = ("name", "notes")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = (
        "id", "generated_by", "available_count", "redeemed_count",
        "voided_count", "created_at", "updated_at",
    )
    raw_id_fields = ("plan",)
    inlines = [VoucherInline]

    fieldsets = (
        (_("Batch Details"), {
            "fields": ("id", "name", "plan", "quantity", "notes"),
        }),
        (_("Validity"), {
            "fields": ("valid_from", "valid_until"),
        }),
        (_("Stats"), {
            "fields": ("available_count", "redeemed_count", "voided_count"),
            "description": _("Live counts — computed from voucher records."),
        }),
        (_("Meta"), {
            "fields": ("generated_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Only stamp generated_by on creation
            obj.generated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        "code", "batch", "status_badge",
        "redeemed_by", "redeemed_at", "voided_by",
    )
    list_filter = ("status", "batch__plan")
    search_fields = ("code", "redeemed_by__username", "batch__name")
    ordering = ("code",)
    readonly_fields = (
        "id", "code", "redeemed_by", "redeemed_at",
        "voided_by", "created_at", "updated_at",
    )
    raw_id_fields = ("batch",)

    fieldsets = (
        (_("Code"), {"fields": ("id", "code", "batch", "status")}),
        (_("Redemption"), {"fields": ("redeemed_by", "redeemed_at")}),
        (_("Void"), {"fields": ("voided_by", "void_reason")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["void_vouchers"]

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colours = {
            "unused":   ("green",  "◦ Unused"),
            "redeemed": ("blue",   "✓ Redeemed"),
            "expired":  ("grey",   "⏰ Expired"),
            "voided":   ("red",    "✗ Voided"),
        }
        colour, label = colours.get(obj.status, ("black", obj.status))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)

    @admin.action(description=_("Void selected unused vouchers"))
    def void_vouchers(self, request, queryset):
        count = 0
        for voucher in queryset.filter(status=Voucher.VoucherStatus.UNUSED):
            voucher.void(admin=request.user, reason="Voided via admin bulk action.")
            count += 1
        self.message_user(request, f"{count} voucher(s) voided.")
