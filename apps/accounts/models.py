"""
apps/accounts/models.py
-----------------------
Custom admin user model with role-based access control.
Replaces Django's default User — defined early so AUTH_USER_MODEL can point here.
"""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator

from utils.mixins import BaseModel
from utils.validators import validate_zimbabwe_phone
from .managers import AdminUserManager


class Role(BaseModel):
    """
    Named role with a set of permissions (e.g. Super Admin, Support Agent).
    Uses Django's built-in Permission model for granular control.
    """

    class RoleLevel(models.IntegerChoices):
        SUPER_ADMIN = 1, _("Super Admin")
        ADMIN = 2, _("Admin")
        SUPPORT = 3, _("Support Agent")
        VIEWER = 4, _("Read-Only Viewer")

    name = models.CharField(
        max_length=80,
        unique=True,
        verbose_name=_("Role Name"),
        help_text=_("Human-readable name for this role."),
    )
    level = models.PositiveSmallIntegerField(
        choices=RoleLevel.choices,
        default=RoleLevel.SUPPORT,
        verbose_name=_("Role Level"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        related_name="roles",
        verbose_name=_("Permissions"),
    )

    class Meta:
        db_table = "accounts_role"
        ordering = ["level"]
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")

    def __str__(self):
        return f"{self.name} (Level {self.level})"

    def clean(self):
        self.name = self.name.strip().title()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AdminUser(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Platform administrator — NOT a hotspot subscriber.
    Authenticated via JWT; can manage subscribers, vouchers, and system config.
    """

    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        verbose_name=_("Email Address"),
    )
    full_name = models.CharField(
        max_length=150,
        verbose_name=_("Full Name"),
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_zimbabwe_phone],
        verbose_name=_("Phone Number"),
    )
    role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_users",
        verbose_name=_("Role"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Inactive admins cannot log in."),
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_("Staff Status"),
        help_text=_("Required for Django admin site access."),
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Last Login IP"),
    )
    failed_login_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Failed Login Attempts"),
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Locked Until"),
        help_text=_("Account is locked from logging in until this time."),
    )

    # Override PermissionsMixin M2M fields to prevent reverse-accessor clash
    # with auth.User when both models co-exist (AUTH_USER_MODEL swap).
    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="admin_users",
        related_query_name="admin_user",
        verbose_name=_("Groups"),
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        related_name="admin_users",
        related_query_name="admin_user",
        verbose_name=_("User Permissions"),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = AdminUserManager()

    class Meta:
        db_table = "accounts_admin_user"
        ordering = ["full_name"]
        verbose_name = _("Administrator")
        verbose_name_plural = _("Administrators")
        indexes = [
            models.Index(fields=["email"], name="idx_adminuser_email"),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone

        self.email = self.email.strip().lower()
        self.full_name = self.full_name.strip()

        if not self.full_name:
            raise ValidationError({"full_name": _("Full name cannot be blank.")})

        if len(self.full_name) < 3:
            raise ValidationError(
                {"full_name": _("Full name must be at least 3 characters.")}
            )

        if self.locked_until and self.locked_until < timezone.now():
            # Auto-clear expired lockouts on save
            self.locked_until = None
            self.failed_login_count = 0

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Business logic helpers
    # ------------------------------------------------------------------

    @property
    def is_locked(self) -> bool:
        from django.utils import timezone
        return bool(self.locked_until and self.locked_until > timezone.now())

    def record_failed_login(self) -> None:
        """Increment failure counter; lock account after 5 consecutive failures."""
        from django.utils import timezone
        from datetime import timedelta

        self.failed_login_count += 1
        if self.failed_login_count >= 5:
            self.locked_until = timezone.now() + timedelta(minutes=30)
        self.save(update_fields=["failed_login_count", "locked_until"])

    def reset_login_failures(self) -> None:
        self.failed_login_count = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_count", "locked_until"])