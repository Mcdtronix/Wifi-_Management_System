"""
apps/radius/models.py
---------------------
FreeRADIUS integration models and RADIUS protocol configuration.
Stores reply attributes and radius-specific settings.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.mixins import BaseModel


class RadiusReplyAttribute(BaseModel):
    """
    RADIUS reply attribute configuration.
    Maps Django data to RADIUS response attributes sent to NAS (access point).
    
    Example:
    - Attribute: WISPr-Bandwidth-Max-Down
    - Value Template: "{bandwidth_profile.download_bps}"
    """

    class AttributeType(models.TextChoices):
        BANDWIDTH_UP = "WISPr-Bandwidth-Max-Up", _("Bandwidth Max Upload")
        BANDWIDTH_DOWN = "WISPr-Bandwidth-Max-Down", _("Bandwidth Max Download")
        SESSION_TIMEOUT = "Session-Timeout", _("Session Timeout")
        IDLE_TIMEOUT = "Idle-Timeout", _("Idle Timeout")
        ACCT_INTERIM_INTERVAL = "Acct-Interim-Interval", _("Accounting Interim Interval")
        FRAMED_IP_ADDRESS = "Framed-IP-Address", _("Framed IP Address")
        REPLY_MESSAGE = "Reply-Message", _("Reply Message")
        FILTER_ID = "Filter-Id", _("Filter ID")
        CLASS = "Class", _("Class")
        CUSTOM = "custom", _("Custom Attribute")

    name = models.CharField(
        max_length=150,
        verbose_name=_("Attribute Name"),
    )
    attribute_type = models.CharField(
        max_length=100,
        choices=AttributeType.choices,
        verbose_name=_("RADIUS Attribute Type"),
    )
    value_template = models.TextField(
        verbose_name=_("Value Template"),
        help_text=_("Template string; use {field} syntax for variable substitution."),
    )
    operator = models.CharField(
        max_length=5,
        choices=[
            (":=", _("Assign")),
            ("+=", _("Add")),
            ("==", _("Compare")),
            ("!=", _("Not Equal")),
            (">", _("Greater Than")),
            ("<", _("Less Than")),
        ],
        default=":=",
        verbose_name=_("Operator"),
    )
    is_reply = models.BooleanField(
        default=True,
        verbose_name=_("Reply Attribute"),
        help_text=_("If False, this is a check item."),
    )
    is_enabled = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Enabled"),
    )
    priority = models.PositiveSmallIntegerField(
        default=100,
        verbose_name=_("Priority"),
        help_text=_("Lower = higher priority in RADIUS reply."),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        db_table = "radius_reply_attribute"
        ordering = ["priority", "name"]
        verbose_name = _("RADIUS Reply Attribute")
        verbose_name_plural = _("RADIUS Reply Attributes")

    def __str__(self):
        return f"{self.name} ({self.attribute_type})"


class RadiusConfig(BaseModel):
    """
    Global FreeRADIUS server configuration.
    Connection details and policy settings.
    """

    server_host = models.CharField(
        max_length=255,
        verbose_name=_("RADIUS Server Host"),
        help_text=_("Hostname or IP of FreeRADIUS server."),
    )
    server_port = models.PositiveIntegerField(
        default=1812,
        verbose_name=_("Server Port"),
    )
    shared_secret = models.CharField(
        max_length=255,
        verbose_name=_("Shared Secret"),
        help_text=_("Authentication secret between Django and FreeRADIUS. Keep secure!"),
    )
    accounting_port = models.PositiveIntegerField(
        default=1813,
        verbose_name=_("Accounting Port"),
    )
    
    # Timeouts
    auth_timeout_seconds = models.PositiveSmallIntegerField(
        default=5,
        verbose_name=_("Authentication Timeout (seconds)"),
    )
    max_retries = models.PositiveSmallIntegerField(
        default=3,
        verbose_name=_("Max Retries"),
    )
    
    # Accounting
    accounting_enabled = models.BooleanField(
        default=True,
        verbose_name=_("Accounting Enabled"),
    )
    interim_update_interval = models.PositiveSmallIntegerField(
        default=600,  # 10 minutes
        verbose_name=_("Interim Update Interval (seconds)"),
    )
    
    # Policy
    allow_concurrent_sessions = models.BooleanField(
        default=False,
        verbose_name=_("Allow Concurrent Sessions"),
    )
    max_sessions_per_user = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("Max Sessions Per User"),
        help_text=_("How many simultaneous logins allowed."),
    )
    session_timeout_seconds = models.PositiveIntegerField(
        default=86400,  # 24 hours
        verbose_name=_("Session Timeout (seconds)"),
    )

    class Meta:
        db_table = "radius_config"
        verbose_name = _("RADIUS Configuration")
        verbose_name_plural = _("RADIUS Configurations")

    def __str__(self):
        return f"FreeRADIUS @ {self.server_host}:{self.server_port}"
