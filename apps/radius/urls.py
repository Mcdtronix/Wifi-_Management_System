"""
apps/radius/urls.py
--------------------
RADIUS authentication-bridge endpoints — routes will be added here as views
are built. These endpoints are called by FreeRADIUS via the rlm_rest module.

Expected endpoints (FreeRADIUS rlm_rest):
    POST radius/authorize/    — Check subscriber credentials & return RADIUS attributes
    POST radius/authenticate/ — Confirm password (PAP / CHAP / MS-CHAP)
    POST radius/postauth/     — Post-authentication hook (log session start)
"""

from django.urls import path

# Views are not yet implemented; urlpatterns is intentionally empty.
# Add routes here as each rlm_rest handler is created in views.py.
urlpatterns: list = []
