"""
apps/subscribers/models.py
--------------------------
Hotspot subscriber (customer) accounts.
Separate from AdminUser — subscribers authenticate through FreeRADIUS
via the captive portal, not through the Django admin.
"""

from django.db import models
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from utils.mixins import BaseModel
from utils.validators import (
    validate_zimbabwe_phone,
    validate_zimbabwe_national_id,
    validate_subscriber_username,
)


class Subscriber(BaseModel):
    """
    A paying customer of the TengarakoData hotspot service.

    One subscriber → one registered device (MAC-bound).
    One subscriber → one active subscription at a time.
    """

    class AccountStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")
        EXPIRED = "expired", _("Expired")
        PENDING = "pending", _("Pending Activation")
        BANNED = "banned", _("Banned")

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    full_name = models.CharField(
        max_length=150,
        verbose_name=_("Full Name"),
    )
    username = models.CharField(
        max_length=32,
        unique=True,
        validators=[validate_subscriber_username],
        verbose_name=_("Username"),
        help_text=_("Used for captive portal and RADIUS authentication."),
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[validate_zimbabwe_phone],
        verbose_name=_("Phone Number"),
        help_text=_("Used for WhatsApp notifications."),
    )
    email = models.EmailField(
        blank=True,
        validators=[EmailValidator()],
        verbose_name=_("Email Address"),
    )
    national_id = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_zimbabwe_national_id],
        verbose_name=_("National ID"),
        help_text=_("Optional. Zimbabwean National ID format: 63-123456-A-75."),
    )

    # ------------------------------------------------------------------
    # Status & Access Control
    # ------------------------------------------------------------------

    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
        db_index=True,
        verbose_name=_("Account Status"),
    )
    suspension_reason = models.TextField(
        blank=True,
        verbose_name=_("Suspension Reason"),
        help_text=_("Populated when account is suspended or banned."),
    )

    # ------------------------------------------------------------------
    # RADIUS password (stored hashed via FreeRADIUS NT-hash or bcrypt)
    # ------------------------------------------------------------------

    radius_password = models.CharField(
        max_length=255,
        verbose_name=_("RADIUS Password (hashed)"),
        help_text=_("Never store plaintext. Use set_radius_password()."),
    )

    # ------------------------------------------------------------------
    # Relations (FK targets defined in other apps; use string references)
    # ------------------------------------------------------------------

    created_by = models.ForeignKey(
        "accounts.AdminUser",
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_subscribers",
        verbose_name=_("Created By"),
    )

    class Meta:
        db_table = "subscribers_subscriber"
        ordering = ["full_name"]
        verbose_name = _("Subscriber")
        verbose_name_plural = _("Subscribers")
        indexes = [
            models.Index(fields=["username"], name="idx_subscriber_username"),
            models.Index(fields=["phone_number"], name="idx_subscriber_phone"),
            models.Index(fields=["account_status"], name="idx_subscriber_status"),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.username})"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        self.full_name = self.full_name.strip()
        self.username = self.username.strip().lower()
        self.email = self.email.strip().lower()
        self.national_id = self.national_id.strip().upper()

        if not self.full_name:
            raise ValidationError({"full_name": _("Full name cannot be blank.")})

        if len(self.full_name) < 2:
            raise ValidationError(
                {"full_name": _("Full name must be at least 2 characters.")}
            )

        # Suspension reason required when suspending or banning
        if self.account_status in (
            self.AccountStatus.SUSPENDED,
            self.AccountStatus.BANNED,
        ) and not self.suspension_reason:
            raise ValidationError(
                {
                    "suspension_reason": _(
                        "A reason is required when suspending or banning an account."
                    )
                }
            )

        # Radius password must be set
        if not self.radius_password:
            raise ValidationError(
                {"radius_password": _("A RADIUS password hash must be set.")}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Business helpers
    # ------------------------------------------------------------------

    def set_radius_password(self, raw_password: str) -> None:
        """Hash and store the subscriber's RADIUS password."""
        import hashlib
        self.radius_password = hashlib.sha256(raw_password.encode()).hexdigest()

    def suspend(self, reason: str, admin) -> None:
        self.account_status = self.AccountStatus.SUSPENDED
        self.suspension_reason = reason
        self.save(update_fields=["account_status", "suspension_reason", "updated_at"])

    def activate(self) -> None:
        self.account_status = self.AccountStatus.ACTIVE
        self.suspension_reason = ""
        self.save(update_fields=["account_status", "suspension_reason", "updated_at"])

    @property
    def is_accessible(self) -> bool:
        """True when the subscriber can be granted internet access."""
        return self.account_status == self.AccountStatus.ACTIVE

    @property
    def is_staff(self) -> bool:
        """Subscribers are never staff. Required for DRF IsAdminUser permission checks."""
        return False

    @property
    def is_authenticated(self) -> bool:
        """Required for DRF IsAuthenticated permission checks."""
        return True

    @property
    def is_anonymous(self) -> bool:
        """Required for Django compatibility."""
        return False