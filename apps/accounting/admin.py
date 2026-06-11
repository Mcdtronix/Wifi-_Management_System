"""
apps/accounting/admin.py
-------------------------
Django admin for RADIUS accounting records and aggregated sessions.
These are primarily read-only — data is written by FreeRADIUS / signal handlers.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import RadiusAccounting, Session


@admin.register(RadiusAccounting)
class RadiusAccountingAdmin(admin.ModelAdmin):
    list_display = (
        "username", "acctstatustype", "nasipaddress",
        "callingstationid", "acctstarttime", "acctstoptime",
        "data_summary", "subscriber",
    )
    list_filter = ("acctstatustype",)
    search_fields = ("username", "callingstationid", "acctuniqueid", "subscriber__username")
    date_hierarchy = "acctstarttime"
    ordering = ("-acctstarttime",)
    readonly_fields = tuple(
        f.name for f in RadiusAccounting._meta.get_fields()
        if hasattr(f, "name") and not f.many_to_many
    )

    fieldsets = (
        (_("Session Identity"), {
            "fields": ("acctuniqueid", "username", "realm", "subscriber"),
        }),
        (_("Network"), {
            "fields": ("nasipaddress", "nasportid", "nasporttype",
                       "calledstationid", "callingstationid", "framedipaddress"),
        }),
        (_("Timing"), {
            "fields": ("acctstatustype", "acctstarttime", "acctstoptime", "acctsessiontime"),
        }),
        (_("Data Transfer"), {
            "fields": ("acctinputoctets", "acctoutputoctets"),
        }),
        (_("Connection Info"), {
            "fields": ("acctauthentic", "acctterminatecause", "servicetype",
                       "framedprotocol", "connectinfo_start", "connectinfo_stop"),
            "classes": ("collapse",),
        }),
    )

    def has_add_permission(self, request):
        return False  # Written by FreeRADIUS rlm_rest only

    def has_change_permission(self, request, obj=None):
        return False  # Immutable accounting records

    @admin.display(description=_("Data"))
    def data_summary(self, obj):
        total_mb = obj.total_bytes / 1024 / 1024
        return f"↑{obj.acctinputoctets // 1024 // 1024} MB  ↓{obj.acctoutputoctets // 1024 // 1024} MB  ({total_mb:.1f} MB total)"


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "subscriber", "mac_address", "client_ip", "state_badge",
        "started_at", "ended_at", "duration_display", "data_summary",
    )
    list_filter = ("state",)
    search_fields = ("subscriber__username", "subscriber__full_name", "mac_address", "client_ip")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("subscriber", "radius_record")

    fieldsets = (
        (_("Session"), {
            "fields": ("id", "subscriber", "radius_record", "mac_address", "client_ip", "state"),
        }),
        (_("Timing"), {
            "fields": ("started_at", "ended_at", "duration_seconds", "terminate_cause"),
        }),
        (_("Data"), {
            "fields": ("upload_bytes", "download_bytes"),
        }),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False  # Written by accounting signal handlers only

    @admin.display(description=_("State"))
    def state_badge(self, obj):
        colours = {
            "active":      ("green",  "● Active"),
            "closed":      ("grey",   "◼ Closed"),
            "interrupted": ("orange", "⚠ Interrupted"),
        }
        colour, label = colours.get(obj.state, ("black", obj.state))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', colour, label)

    @admin.display(description=_("Duration"))
    def duration_display(self, obj):
        if not obj.duration_seconds:
            return "—"
        h, rem = divmod(obj.duration_seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

    @admin.display(description=_("Data"))
    def data_summary(self, obj):
        up_mb = obj.upload_bytes / 1024 / 1024
        down_mb = obj.download_bytes / 1024 / 1024
        return f"↑{up_mb:.1f} MB  ↓{down_mb:.1f} MB"
