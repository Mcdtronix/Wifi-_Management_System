"""
apps/subscriptions/models.py
-----------------------------
Internet subscription plans and per-subscriber active subscriptions.
Plans define pricing, duration, bandwidth tier, and quota policy.
A Subscription is the live instance of a plan assigned to a subscriber.
"""

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from utils.mixins import BaseModel
from utils.validators import validate_positive_decimal, validate_positive_integer


class Plan(BaseModel):
    """
    A reusable internet package template (e.g. Silver Monthly, Gold Weekly).
    Admins create plans; subscribers are assigned to plans.
    """

    class PlanType(models.TextChoices):
        DAILY = "daily", _("Daily")
        WEEKLY = "weekly", _("Weekly")
        MONTHLY = "monthly", _("Monthly")
        CUSTOM = "custom", _("Custom")

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Plan Name"),
    )
    plan_type = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        verbose_name=_("Plan Type"),
    )
    duration_days = models.PositiveIntegerField(
        validators=[validate_positive_integer],
        verbose_name=_("Duration (Days)"),
        help_text=_("Number of calendar days the plan is valid."),
    )
    price_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[validate_positive_decimal],
        verbose_name=_("Price (USD)"),
    )

    # Bandwidth tier (linked to BandwidthProfile in bandwidth app)
    bandwidth_profile = models.ForeignKey(
        "bandwidth.BandwidthProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plans",
        verbose_name=_("Bandwidth Profile"),
    )

    # Quota policy (linked to QuotaPolicy in quota app)
    quota_policy = models.ForeignKey(
        "quota.QuotaPolicy",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plans",
        verbose_name=_("Daily Quota Policy"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Available for Purchase"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    grace_period_hours = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Grace Period (Hours)"),
        help_text=_(
            "Hours of continued access after expiry before the account is fully blocked. "
            "Set to 0 for immediate cutoff."
        ),
    )

    class Meta:
        db_table = "subscriptions_plan"
        ordering = ["plan_type", "price_usd"]
        verbose_name = _("Plan")
        verbose_name_plural = _("Plans")

    def __str__(self):
        return f"{self.name} — ${self.price_usd} / {self.duration_days}d"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        self.name = self.name.strip()

        if not self.name:
            raise ValidationError({"name": _("Plan name cannot be blank.")})

        # Enforce sensible duration boundaries per plan type
        type_limits = {
            self.PlanType.DAILY: (1, 1),
            self.PlanType.WEEKLY: (7, 7),
            self.PlanType.MONTHLY: (28, 31),
            self.PlanType.CUSTOM: (1, 365),
        }
        if self.plan_type in type_limits:
            min_d, max_d = type_limits[self.plan_type]
            if not (min_d <= self.duration_days <= max_d):
                raise ValidationError(
                    {
                        "duration_days": _(
                            f"A {self.get_plan_type_display()} plan must have a "
                            f"duration between {min_d} and {max_d} days."
                        )
                    }
                )

        if self.price_usd < Decimal("0.50"):
            raise ValidationError(
                {"price_usd": _("Plan price must be at least $0.50.")}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Subscription(BaseModel):
    """
    A live subscription instance — one plan assigned to one subscriber.
    Tracks activation, expiry, renewal history, and current access state.

    Business Rules:
    - A subscriber may have only ONE active subscription at a time.
    - On renewal, a new Subscription record is created (history preserved).
    - Expiry is monitored by a Celery Beat task in tasks.py.
    """

    class SubscriptionStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        EXPIRED = "expired", _("Expired")
        SUSPENDED = "suspended", _("Suspended")
        CANCELLED = "cancelled", _("Cancelled")
        GRACE = "grace", _("In Grace Period")

    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name=_("Subscriber"),
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        verbose_name=_("Plan"),
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
        db_index=True,
        verbose_name=_("Status"),
    )
    activated_at = models.DateTimeField(
        verbose_name=_("Activated At"),
    )
    expires_at = models.DateTimeField(
        db_index=True,
        verbose_name=_("Expires At"),
    )
    grace_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Grace Period Ends At"),
    )

    # Voucher redemption (optional — populated if subscriber paid via voucher)
    redeemed_voucher = models.OneToOneField(
        "vouchers.Voucher",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subscription",
        verbose_name=_("Redeemed Voucher"),
    )

    # Audit
    created_by = models.ForeignKey(
        "accounts.AdminUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_subscriptions",
        verbose_name=_("Created By"),
    )
    amount_paid_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Amount Paid (USD)"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
    )

    class Meta:
        db_table = "subscriptions_subscription"
        ordering = ["-activated_at"]
        verbose_name = _("Subscription")
        verbose_name_plural = _("Subscriptions")
        constraints = [
            models.UniqueConstraint(
                fields=["subscriber"],
                condition=models.Q(status="active"),
                name="uq_one_active_subscription_per_subscriber",
            )
        ]
        indexes = [
            models.Index(fields=["subscriber", "status"], name="idx_sub_subscriber_status"),
            models.Index(fields=["expires_at"], name="idx_sub_expires_at"),
        ]

    def __str__(self):
        return (
            f"{self.subscriber.username} — {self.plan.name} "
            f"[{self.status}] expires {self.expires_at:%Y-%m-%d}"
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        from django.utils import timezone

        if self.activated_at and self.expires_at:
            if self.expires_at <= self.activated_at:
                raise ValidationError(
                    _("Expiry date must be after the activation date.")
                )

        if self.amount_paid_usd < Decimal("0.00"):
            raise ValidationError(
                {"amount_paid_usd": _("Amount paid cannot be negative.")}
            )

        # Grace period end must be after expiry
        if self.grace_ends_at and self.expires_at:
            if self.grace_ends_at <= self.expires_at:
                raise ValidationError(
                    _("Grace period end must be after the subscription expiry.")
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Class-level factory
    # ------------------------------------------------------------------

    @classmethod
    def create_for_subscriber(cls, subscriber, plan, admin=None, voucher=None):
        """
        Properly initialise a new subscription, calculating expiry from plan duration.
        Cancels any existing active subscription first.
        """
        from django.utils import timezone
        from datetime import timedelta

        # Cancel existing active subscription
        cls.objects.filter(
            subscriber=subscriber,
            status=cls.SubscriptionStatus.ACTIVE,
        ).update(status=cls.SubscriptionStatus.CANCELLED)

        now = timezone.now()
        expires = now + timedelta(days=plan.duration_days)
        grace_ends = None
        if plan.grace_period_hours:
            grace_ends = expires + timedelta(hours=plan.grace_period_hours)

        return cls.objects.create(
            subscriber=subscriber,
            plan=plan,
            status=cls.SubscriptionStatus.ACTIVE,
            activated_at=now,
            expires_at=expires,
            grace_ends_at=grace_ends,
            amount_paid_usd=plan.price_usd,
            redeemed_voucher=voucher,
            created_by=admin,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        from django.utils import timezone
        return (
            self.status == self.SubscriptionStatus.ACTIVE
            and self.expires_at > timezone.now()
        )

    @property
    def is_in_grace(self) -> bool:
        from django.utils import timezone
        now = timezone.now()
        return (
            self.status in (self.SubscriptionStatus.GRACE, self.SubscriptionStatus.EXPIRED)
            and self.grace_ends_at is not None
            and self.grace_ends_at > now
        )