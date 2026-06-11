"""
apps/captive_portal/urls.py
----------------------------
Captive portal endpoints — routes will be added here as views are built.

Expected endpoints:
    GET  portal/              — Serve the captive portal splash page
    POST portal/authenticate/ — RADIUS-backed credential check
    GET  portal/status/       — Check if the subscriber's session is active
"""

from django.urls import path

# Views are not yet implemented; urlpatterns is intentionally empty.
# Add routes here as each view is created in views.py.
urlpatterns: list = []
