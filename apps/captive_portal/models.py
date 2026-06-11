"""
apps/captive_portal/models.py
------------------------------
Captive portal session management and configuration.
Tracks user-facing login sessions and portal settings.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.mixins import BaseModel


class PortalConfig(BaseModel):
    """
    Global configuration for the captive portal.
    One record per deployment; controls branding and behavior.
    """

    site_name = models.CharField(
        max_length=100,
        default="TengarakoData",
        verbose_name=_("Site Name"),
    )
    site_url = models.URLField(
        verbose_name=_("Portal URL"),
        help_text=_("Public URL where users access the portal."),
    )
    logo_url = models.URLField(
        blank=True,
        verbose_name=_("Logo URL"),
    )
    header_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Header Text"),
    )
    footer_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Footer Text"),
    )
    primary_color = models.CharField(
        max_length=7,
        default="#2563eb",
        verbose_name=_("Primary Color (Hex)"),
    )
    secondary_color = models.CharField(
        max_length=7,
        default="#1e40af",
        verbose_name=_("Secondary Color (Hex)"),
    )
    
    # Session settings
    session_timeout_minutes = models.PositiveSmallIntegerField(
        default=1440,  # 24 hours
        verbose_name=_("Session Timeout (minutes)"),
    )
    allow_remember_me = models.BooleanField(
        default=True,
        verbose_name=_("Allow Remember Me"),
    )
    require_email = models.BooleanField(
        default=False,
        verbose_name=_("Require Email"),
    )
    require_phone = models.BooleanField(
        default=False,
        verbose_name=_("Require Phone"),
    )
    
    # Terms and conditions
    show_terms = models.BooleanField(
        default=True,
        verbose_name=_("Show Terms & Conditions"),
    )
    terms_text = models.TextField(
        blank=True,
        verbose_name=_("Terms & Conditions"),
    )
    terms_version = models.CharField(
        max_length=20,
        default="1.0",
        verbose_name=_("Terms Version"),
    )

    class Meta:
        db_table = "captive_portal_config"
        verbose_name = _("Portal Configuration")
        verbose_name_plural = _("Portal Configurations")

    def __str__(self):
        return f"Portal Config: {self.site_name}"


class PortalSession(BaseModel):
    """
    User session on the captive portal.
    Tracks login attempts, IP address, user agent, etc.
    """

    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="portal_sessions",
        verbose_name=_("Subscriber"),
    )
    session_key = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("Session Key"),
    )
    ip_address = models.GenericIPAddressField(
        verbose_name=_("IP Address"),
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_("User Agent"),
    )
    mac_address = models.CharField(
        max_length=17,
        blank=True,
        verbose_name=_("Device MAC"),
    )
    
    # Session lifecycle
    logged_in_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Logged In At"),
    )
    last_activity_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Activity"),
    )
    logged_out_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Logged Out At"),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Active"),
    )
    logout_reason = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Logout Reason"),
        help_text=_("E.g. 'manual', 'timeout', 'subscription_expired'."),
    )

    class Meta:
        db_table = "captive_portal_session"
        ordering = ["-logged_in_at"]
        verbose_name = _("Portal Session")
        verbose_name_plural = _("Portal Sessions")
        indexes = [
            models.Index(fields=["subscriber", "-logged_in_at"], name="idx_portal_sub_date"),
            models.Index(fields=["is_active"], name="idx_portal_active"),
        ]

    def __str__(self):
        return f"{self.subscriber.username} @ {self.ip_address} ({self.logged_in_at})"
