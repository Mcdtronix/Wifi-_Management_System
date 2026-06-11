"""
apps/accounting/models.py
--------------------------
RADIUS accounting records and aggregated session data.
FreeRADIUS posts Accounting-Start, Accounting-Update, and Accounting-Stop
packets to our API. These are stored here verbatim and also used to update
DailyQuotaUsage in real time.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from utils.mixins import BaseModel


class RadiusAccounting(models.Model):
    """
    Raw RADIUS accounting record — one row per accounting packet received.
    This mirrors the standard radacct schema used by FreeRADIUS / PostgreSQL module.

    Intentionally uses integer PK (matching FreeRADIUS conventions) and no
    BaseModel UUID — radacct tables are append-only and extremely high-volume.
    """

    class AcctStatusType(models.TextChoices):
        START = "Start", _("Session Start")
        STOP = "Stop", _("Session Stop")
        ALIVE = "Alive", _("Interim Update")

    # FreeRADIUS standard fields
    acctuniqueid = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("Accounting Unique ID"),
        help_text=_("Unique session identifier from FreeRADIUS."),
    )
    username = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name=_("Username"),
    )
    realm = models.CharField(max_length=64, blank=True, verbose_name=_("Realm"))
    nasipaddress = models.GenericIPAddressField(
        verbose_name=_("NAS IP Address"),
        help_text=_("IP of the TP-Link EAP110 access point."),
    )
    nasportid = models.CharField(max_length=32, blank=True, verbose_name=_("NAS Port ID"))
    nasporttype = models.CharField(max_length=32, blank=True, verbose_name=_("NAS Port Type"))
    acctstarttime = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Session Start Time")
    )
    acctstoptime = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Session Stop Time")
    )
    acctsessiontime = models.BigIntegerField(
        default=0, verbose_name=_("Session Duration (seconds)")
    )
    acctauthentic = models.CharField(max_length=32, blank=True, verbose_name=_("Auth Method"))
    acctstatustype = models.CharField(
        max_length=32,
        choices=AcctStatusType.choices,
        verbose_name=_("Status Type"),
    )
    acctinputoctets = models.BigIntegerField(
        default=0, verbose_name=_("Input (Upload) Bytes")
    )
    acctoutputoctets = models.BigIntegerField(
        default=0, verbose_name=_("Output (Download) Bytes")
    )
    calledstationid = models.CharField(
        max_length=50, blank=True, verbose_name=_("Called Station ID (AP MAC)")
    )
    callingstationid = models.CharField(
        max_length=50,
        db_index=True,
        blank=True,
        verbose_name=_("Calling Station ID (Client MAC)"),
    )
    framedipaddress = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("Client IP Address")
    )
    acctterminatecause = models.CharField(
        max_length=32, blank=True, verbose_name=_("Terminate Cause")
    )
    servicetype = models.CharField(max_length=32, blank=True, verbose_name=_("Service Type"))
    framedprotocol = models.CharField(max_length=32, blank=True, verbose_name=_("Framed Protocol"))
    connectinfo_start = models.TextField(blank=True, verbose_name=_("Connect Info (Start)"))
    connectinfo_stop = models.TextField(blank=True, verbose_name=_("Connect Info (Stop)"))

    # FK to our subscriber (denormalised for fast lookup)
    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="radius_sessions",
        verbose_name=_("Subscriber"),
    )

    class Meta:
        db_table = "radacct"          # Match FreeRADIUS PostgreSQL module table name
        ordering = ["-acctstarttime"]
        verbose_name = _("RADIUS Accounting Record")
        verbose_name_plural = _("RADIUS Accounting Records")
        indexes = [
            models.Index(fields=["username", "acctstarttime"], name="idx_radacct_user_start"),
            models.Index(fields=["callingstationid"], name="idx_radacct_mac"),
            models.Index(fields=["acctstoptime"], name="idx_radacct_stop"),
        ]

    def __str__(self):
        return f"[{self.acctstatustype}] {self.username} — {self.acctstarttime}"

    def clean(self):
        if self.acctinputoctets < 0:
            raise ValidationError(
                {"acctinputoctets": _("Input octets cannot be negative.")}
            )
        if self.acctoutputoctets < 0:
            raise ValidationError(
                {"acctoutputoctets": _("Output octets cannot be negative.")}
            )
        if self.acctsessiontime < 0:
            raise ValidationError(
                {"acctsessiontime": _("Session time cannot be negative.")}
            )
        if self.acctstoptime and self.acctstarttime:
            if self.acctstoptime < self.acctstarttime:
                raise ValidationError(
                    _("Session stop time cannot be before session start time.")
                )

    @property
    def total_bytes(self) -> int:
        return self.acctinputoctets + self.acctoutputoctets


class Session(BaseModel):
    """
    Aggregated view of a subscriber's session — one row per login session.
    Built from RadiusAccounting Start/Stop pairs for cleaner reporting.
    Not written by FreeRADIUS directly; maintained by our accounting signal handler.
    """

    class SessionState(models.TextChoices):
        ACTIVE = "active", _("Active")
        CLOSED = "closed", _("Closed")
        INTERRUPTED = "interrupted", _("Interrupted (No Stop packet received)")

    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name=_("Subscriber"),
    )
    radius_record = models.OneToOneField(
        RadiusAccounting,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="session",
        verbose_name=_("RADIUS Record"),
    )
    mac_address = models.CharField(
        max_length=17,
        verbose_name=_("Device MAC"),
    )
    client_ip = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("Client IP")
    )
    state = models.CharField(
        max_length=20,
        choices=SessionState.choices,
        default=SessionState.ACTIVE,
        db_index=True,
        verbose_name=_("Session State"),
    )
    started_at = models.DateTimeField(verbose_name=_("Started At"))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Ended At"))
    duration_seconds = models.BigIntegerField(
        default=0, verbose_name=_("Duration (seconds)")
    )
    upload_bytes = models.BigIntegerField(default=0, verbose_name=_("Upload (bytes)"))
    download_bytes = models.BigIntegerField(default=0, verbose_name=_("Download (bytes)"))
    terminate_cause = models.CharField(
        max_length=64, blank=True, verbose_name=_("Terminate Cause")
    )

    class Meta:
        db_table = "accounting_session"
        ordering = ["-started_at"]
        verbose_name = _("Session")
        verbose_name_plural = _("Sessions")
        indexes = [
            models.Index(fields=["subscriber", "started_at"], name="idx_session_sub_start"),
            models.Index(fields=["state"], name="idx_session_state"),
        ]

    def __str__(self):
        duration = f"{self.duration_seconds // 60}m" if self.duration_seconds else "ongoing"
        return f"{self.subscriber.username} | {self.started_at:%Y-%m-%d %H:%M} | {duration}"

    def clean(self):
        if self.upload_bytes < 0:
            raise ValidationError({"upload_bytes": _("Upload bytes cannot be negative.")})
        if self.download_bytes < 0:
            raise ValidationError({"download_bytes": _("Download bytes cannot be negative.")})
        if self.duration_seconds < 0:
            raise ValidationError({"duration_seconds": _("Duration cannot be negative.")})
        if self.ended_at and self.started_at:
            if self.ended_at < self.started_at:
                raise ValidationError(_("Session end time must be after start time."))

    @property
    def total_bytes(self) -> int:
        return self.upload_bytes + self.download_bytes

    @property
    def total_mb(self) -> float:
        return self.total_bytes / 1024 ** 2