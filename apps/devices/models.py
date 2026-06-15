"""
apps/devices/models.py
----------------------
MAC address binding per subscriber.
One active device per subscriber at a time — enforces anti-sharing policy.
Device change requests go through admin approval before the old MAC is released.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from utils.mixins import BaseModel
from utils.validators import validate_mac_address


class Device(BaseModel):
    """
    A single physical device (identified by MAC address) bound to a subscriber.

    Rules:
    - Only one Device per subscriber may be `is_primary=True` at a time.
    - The primary device is the only one that passes RADIUS MAC-auth.
    - Historical devices are kept for audit trail; is_primary=False means inactive.
    """

    class DeviceStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        REPLACED = "replaced", _("Replaced")
        REVOKED = "revoked", _("Revoked (Fraud)")
        PENDING = "pending", _("Pending Approval")

    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="devices",
        verbose_name=_("Subscriber"),
    )
    mac_address = models.CharField(
        max_length=17,
        unique=True,
        validators=[validate_mac_address],
        verbose_name=_("MAC Address"),
        help_text=_("Format: AA:BB:CC:DD:EE:FF"),
    )
    device_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Device Name"),
        help_text=_("Optional label, e.g. 'Samsung Galaxy A54'."),
    )
    browser_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("Browser Fingerprint"),
        help_text=_("Hash to prevent MAC spoofing."),
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_("User Agent"),
    )
    status = models.CharField(
        max_length=20,
        choices=DeviceStatus.choices,
        default=DeviceStatus.ACTIVE,
        db_index=True,
        verbose_name=_("Status"),
    )
    is_primary = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Primary Device"),
        help_text=_("Only the primary device is used for RADIUS MAC authentication."),
    )
    first_seen_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("First Seen"),
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Seen"),
    )
    registered_by = models.ForeignKey(
        "accounts.AdminUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registered_devices",
        verbose_name=_("Registered By"),
        help_text=_("Null when auto-registered on first login."),
    )

    class Meta:
        db_table = "devices_device"
        ordering = ["-first_seen_at"]
        verbose_name = _("Device")
        verbose_name_plural = _("Devices")
        constraints = [
            # At most one primary device per subscriber
            models.UniqueConstraint(
                fields=["subscriber"],
                condition=models.Q(is_primary=True, status="active"),
                name="uq_one_primary_device_per_subscriber",
            )
        ]
        indexes = [
            models.Index(fields=["mac_address"], name="idx_device_mac"),
            models.Index(fields=["subscriber", "is_primary"], name="idx_device_subscriber_primary"),
        ]

    def __str__(self):
        label = self.device_name or "Unknown device"
        return f"{label} — {self.mac_address} ({self.subscriber.username})"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        # Normalise MAC to uppercase colon-separated
        if self.mac_address:
            self.mac_address = self.mac_address.upper().replace("-", ":")

        if self.device_name:
            self.device_name = self.device_name.strip()

        # A device cannot be primary and not active simultaneously
        if self.is_primary and self.status != self.DeviceStatus.ACTIVE:
            raise ValidationError(
                _("A device can only be marked as primary when its status is 'Active'.")
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Business helpers
    # ------------------------------------------------------------------

    def revoke(self, reason: str = "Fraud detected") -> None:
        """Revoke device access immediately."""
        self.status = self.DeviceStatus.REVOKED
        self.is_primary = False
        self.save(update_fields=["status", "is_primary", "updated_at"])

    def replace(self) -> None:
        """Mark as replaced when a new device takes over."""
        self.status = self.DeviceStatus.REPLACED
        self.is_primary = False
        self.save(update_fields=["status", "is_primary", "updated_at"])


class DeviceChangeRequest(BaseModel):
    """
    Subscriber-initiated request to swap their registered device.
    An admin must approve before the old MAC is deactivated and the new one bound.
    """

    class RequestStatus(models.TextChoices):
        PENDING = "pending", _("Pending Review")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    class ChangeReason(models.TextChoices):
        LOST = "lost", _("Phone Lost")
        STOLEN = "stolen", _("Phone Stolen")
        NEW_DEVICE = "new_device", _("New Phone Purchased")
        LAPTOP = "laptop", _("Laptop Replacement")
        OTHER = "other", _("Other")

    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="device_change_requests",
        verbose_name=_("Subscriber"),
    )
    old_device = models.ForeignKey(
        Device,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="outgoing_change_requests",
        verbose_name=_("Current Device"),
    )
    new_mac_address = models.CharField(
        max_length=17,
        validators=[validate_mac_address],
        verbose_name=_("Requested New MAC Address"),
    )
    new_device_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("New Device Name"),
    )
    reason = models.CharField(
        max_length=20,
        choices=ChangeReason.choices,
        verbose_name=_("Reason for Change"),
    )
    reason_detail = models.TextField(
        blank=True,
        verbose_name=_("Additional Details"),
    )
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        db_index=True,
        verbose_name=_("Request Status"),
    )
    reviewed_by = models.ForeignKey(
        "accounts.AdminUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_device_requests",
        verbose_name=_("Reviewed By"),
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Reviewed At"),
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_("Rejection Reason"),
    )

    class Meta:
        db_table = "devices_change_request"
        ordering = ["-created_at"]
        verbose_name = _("Device Change Request")
        verbose_name_plural = _("Device Change Requests")

    def __str__(self):
        return (
            f"Device change for {self.subscriber.username} "
            f"→ {self.new_mac_address} [{self.status}]"
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        self.new_mac_address = self.new_mac_address.upper().replace("-", ":")

        # Cannot approve/reject without a reviewer
        if self.status in (
            self.RequestStatus.APPROVED,
            self.RequestStatus.REJECTED,
        ) and not self.reviewed_by_id:
            raise ValidationError(
                _("A reviewing administrator must be assigned before approving or rejecting.")
            )

        # Rejection must have a reason
        if self.status == self.RequestStatus.REJECTED and not self.rejection_reason:
            raise ValidationError(
                {"rejection_reason": _("Please provide a reason for the rejection.")}
            )

        # New MAC must not already be the subscriber's active device
        if self.subscriber_id and self.old_device:
            if self.old_device.mac_address == self.new_mac_address:
                raise ValidationError(
                    _("The new MAC address is the same as the current device.")
                )

        # New MAC must not already be registered to another subscriber
        if Device.objects.filter(
            mac_address=self.new_mac_address,
            status=Device.DeviceStatus.ACTIVE,
        ).exclude(subscriber=self.subscriber).exists():
            raise ValidationError(
                _("This MAC address is already registered to another subscriber.")
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Business helpers
    # ------------------------------------------------------------------

    def approve(self, admin) -> Device:
        """
        Approve the request: deactivate old device and register new one.
        Returns the newly created Device instance.
        """
        from django.utils import timezone

        if self.status != self.RequestStatus.PENDING:
            raise ValidationError(_("Only pending requests can be approved."))

        # Deactivate old device
        if self.old_device:
            self.old_device.replace()

        # Register new device
        new_device = Device.objects.create(
            subscriber=self.subscriber,
            mac_address=self.new_mac_address,
            device_name=self.new_device_name,
            status=Device.DeviceStatus.ACTIVE,
            is_primary=True,
            registered_by=admin,
        )

        self.status = self.RequestStatus.APPROVED
        self.reviewed_by = admin
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

        return new_device

    def reject(self, admin, reason: str) -> None:
        from django.utils import timezone

        if self.status != self.RequestStatus.PENDING:
            raise ValidationError(_("Only pending requests can be rejected."))

        self.status = self.RequestStatus.REJECTED
        self.reviewed_by = admin
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save(
            update_fields=[
                "status", "reviewed_by", "reviewed_at",
                "rejection_reason", "updated_at",
            ]
        )