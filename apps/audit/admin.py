"""
apps/audit/admin.py
--------------------
Django admin for audit logs and admin activity records.
All records are immutable — no add/change permissions.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import AdminActivityLog, AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "action", "severity_badge",
        "actor_display", "actor_ip", "description_excerpt", "source",
    )
    list_filter = ("action", "severity", "source")
    search_fields = (
        "description", "actor_user__full_name", "actor_user__email",
        "actor_subscriber__username", "actor_ip",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = tuple(
        f.name for f in AuditLog._meta.get_fields()
        if hasattr(f, "name") and not f.many_to_many
    ) + ("affected_object",)

    fieldsets = (
        (_("Event"), {
            "fields": ("action", "severity", "source", "description"),
        }),
        (_("Actor"), {
            "fields": ("actor_user", "actor_subscriber", "actor_ip"),
        }),
        (_("Affected Object"), {
            "fields": ("content_type", "object_id", "affected_object"),
        }),
        (_("Changes & Metadata"), {
            "fields": ("changes", "metadata"),
            "classes": ("collapse",),
        }),
        (_("Timestamps"), {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Superuser only; audit logs must be preserved

    @admin.display(description=_("Actor"))
    def actor_display(self, obj):
        if obj.actor_user:
            return f"👤 {obj.actor_user.full_name}"
        if obj.actor_subscriber:
            return f"🙍 {obj.actor_subscriber.username}"
        return "⚙ System"

    @admin.display(description=_("Severity"))
    def severity_badge(self, obj):
        colours = {0: "grey", 1: "blue", 2: "orange", 3: "red", 4: "darkred"}
        labels = {0: "Debug", 1: "Info", 2: "Warning", 3: "Error", 4: "Critical"}
        colour = colours.get(obj.severity, "black")
        label = labels.get(obj.severity, str(obj.severity))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)

    @admin.display(description=_("Description"))
    def description_excerpt(self, obj):
        return obj.description[:80] + "…" if len(obj.description) > 80 else obj.description


@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "admin", "action", "target_user",
        "affected_records_count", "ip_address",
    )
    list_filter = ("action",)
    search_fields = ("admin__full_name", "admin__email", "description", "ip_address")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("id", "admin", "action", "target_user", "description",
                       "ip_address", "user_agent", "affected_records_count", "created_at", "updated_at")

    fieldsets = (
        (_("Action"), {"fields": ("id", "admin", "action", "description")}),
        (_("Target"), {"fields": ("target_user", "affected_records_count")}),
        (_("Request Context"), {"fields": ("ip_address", "user_agent"), "classes": ("collapse",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
