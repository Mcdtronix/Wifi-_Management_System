"""
config/urls.py
--------------
Root URL dispatcher for the TengarakoData Hotspot Management API.

All application endpoints live under the versioned prefix:

    /api/v1/<domain>/

Authentication endpoints (login / logout / token refresh) are surfaced
directly under /api/v1/ so clients follow the conventional pattern:

    POST /api/v1/auth/login/
    POST /api/v1/auth/logout/
    POST /api/v1/auth/token/refresh/

FreeRADIUS (rlm_rest) posts accounting data to:

    POST /api/v1/accounting/radius/

The captive-portal and radius apps expose their own URL modules; routes will
appear automatically here as those modules are built out.

Django's built-in admin UI remains at /admin/ for superuser management.
"""

from django.contrib import admin
from django.urls import include, path

# ---------------------------------------------------------------------------
# Versioned API — all DRF app routers live under this prefix
# ---------------------------------------------------------------------------

# fmt: off
api_v1_patterns = [
    # ── Auth & admin-user management ───────────────────────────────────────
    # Provides: auth/login, auth/logout, auth/token/refresh,
    #           admin/users/, admin/roles/, admin/permissions/
    path("",                    include("apps.accounts.urls")),

    # ── Core subscriber & device management ────────────────────────────────
    path("subscribers/",        include("apps.subscribers.urls")),
    path("devices/",            include("apps.devices.urls")),

    # ── Subscription plans & active subscriptions ──────────────────────────
    # Provides: plans/, subscriptions/
    path("",                    include("apps.subscriptions.urls")),

    # ── Prepaid vouchers ───────────────────────────────────────────────────
    # Provides: vouchers/, vouchers/batches/
    path("vouchers/",           include("apps.vouchers.urls")),

    # ── Network policy ─────────────────────────────────────────────────────
    path("bandwidth/",          include("apps.bandwidth.urls")),
    path("quota/",              include("apps.quota.urls")),

    # ── Accounting & session tracking (FreeRADIUS integration) ─────────────
    # Provides: accounting/radius/ (RADIUS receiver), accounting/records/,
    #           accounting/sessions/
    path("accounting/",         include("apps.accounting.urls")),

    # ── Reporting & dashboards ─────────────────────────────────────────────
    # Provides: reporting/dashboard/, reporting/bandwidth/,
    #           reporting/revenue/, reporting/subscriber-reports/
    path("reporting/",          include("apps.reporting.urls")),

    # ── Notifications ──────────────────────────────────────────────────────
    # Provides: notifications/bulk/, notifications/templates/,
    #           notifications/log/, notifications/preferences/
    path("notifications/",      include("apps.notifications.urls")),

    # ── Fraud detection ────────────────────────────────────────────────────
    # Provides: fraud/rules/, fraud/alerts/
    path("fraud/",              include("apps.fraud.urls")),

    # ── Audit trail ────────────────────────────────────────────────────────
    # Provides: audit/logs/, audit/admin-activity/
    path("audit/",              include("apps.audit.urls")),

    # ── Captive portal (routes added as views are implemented) ─────────────
    path("portal/",             include("apps.captive_portal.urls")),

    # ── RADIUS authentication bridge (routes added as views are built) ──────
    path("radius/",             include("apps.radius.urls")),
]
# fmt: on

# ---------------------------------------------------------------------------
# Root URL table
# ---------------------------------------------------------------------------

urlpatterns = [
    # Django admin — superuser access only
    path("admin/", admin.site.urls),

    # Versioned REST API
    path("api/v1/", include((api_v1_patterns, "api"), namespace="v1")),
]
