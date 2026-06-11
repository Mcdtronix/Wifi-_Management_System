"""
apps/quota/models.py
--------------------
Daily data quota policies and usage tracking.
Quotas are enforced per subscriber per day; usage resets at midnight UTC.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from utils.mixins import BaseModel
from utils.validators import validate_positive_integer


def validate_warning_threshold(value: int) -> None:
    """Quota warning threshold must be between 1 and 100 percent."""
    if not (1 <= value <= 100):
        from django.core.exceptions import ValidationError
        raise ValidationError(
            "Warning threshold must be between 1 and 100 percent."
        )


def validate_soft_limit(value: int) -> None:
    """Soft limit may exceed 100 % to allow short overage before throttling."""
    if not (1 <= value <= 150):
        from django.core.exceptions import ValidationError
        raise ValidationError(
            "Soft limit must be between 1 and 150 percent."
        )


class QuotaPolicy(BaseModel):
    """
    A reusable daily quota template (e.g. 'Basic 2GB', 'Premium 20GB').
    Plans reference QuotaPolicies; subscribers inherit quotas via their active plan.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Policy Name"),
        help_text=_("E.g. 'Basic 2GB Daily', 'Premium Unlimited'."),
    )
    daily_quota_gb = models.FloatField(
        null=True,
        blank=True,
        validators=[validate_positive_integer],
        verbose_name=_("Daily Quota (GB)"),
        help_text=_("Leave blank for unlimited quota."),
    )
    warning_threshold_percent = models.PositiveSmallIntegerField(
        default=80,
        validators=[validate_warning_threshold],
        verbose_name=_("Warning Threshold (%)"),
        help_text=_("Notify user when quota usage exceeds this percentage."),
    )
    soft_limit_percent = models.PositiveSmallIntegerField(
        default=100,
        validators=[validate_soft_limit],
        verbose_name=_("Soft Limit (%)"),
        help_text=_("Speed reduction kicks in at this % of quota. Set >100 for overage tolerance."),
    )
    throttle_speed_mbps = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Throttle Speed (Mbps)"),
        help_text=_("Speed limit when soft limit exceeded. Null = block access."),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        db_table = "quota_policy"
        ordering = ["daily_quota_gb"]
        verbose_name = _("Quota Policy")
        verbose_name_plural = _("Quota Policies")

    def __str__(self):
        if self.daily_quota_gb:
            return f"{self.name} ({self.daily_quota_gb} GB/day)"
        return f"{self.name} (Unlimited)"

    def clean(self):
        self.name = self.name.strip()


class DailyQuotaUsage(BaseModel):
    """
    Daily usage record per subscriber.
    One record per subscriber per calendar day (UTC).
    Usage is incremented by accounting signals from FreeRADIUS.
    """

    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="daily_quota_usage",
        verbose_name=_("Subscriber"),
    )
    usage_date = models.DateField(
        db_index=True,
        verbose_name=_("Usage Date (UTC)"),
        help_text=_("Calendar date in UTC."),
    )
    quota_policy = models.ForeignKey(
        QuotaPolicy,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Applied Quota Policy"),
        help_text=_("Snapshot of policy active on this date."),
    )
    upload_gb = models.FloatField(
        default=0.0,
        verbose_name=_("Upload (GB)"),
    )
    download_gb = models.FloatField(
        default=0.0,
        verbose_name=_("Download (GB)"),
    )
    total_gb = models.FloatField(
        default=0.0,
        db_index=True,
        verbose_name=_("Total (GB)"),
    )
    quota_limit_gb = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("Quota Limit (GB)"),
        help_text=_("Snapshot of quota limit on this date."),
    )
    is_exceeded = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Quota Exceeded"),
    )
    throttled = models.BooleanField(
        default=False,
        verbose_name=_("Speed Throttled"),
        help_text=_("True if soft limit was triggered."),
    )
    blocked = models.BooleanField(
        default=False,
        verbose_name=_("Access Blocked"),
        help_text=_("True if hard limit triggered and no throttle configured."),
    )
    warning_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Warning Notification Sent"),
    )

    class Meta:
        db_table = "quota_daily_usage"
        ordering = ["-usage_date"]
        verbose_name = _("Daily Quota Usage")
        verbose_name_plural = _("Daily Quota Usage")
        unique_together = [["subscriber", "usage_date"]]
        indexes = [
            models.Index(fields=["subscriber", "-usage_date"], name="idx_quota_sub_date"),
            models.Index(fields=["is_exceeded"], name="idx_quota_exceeded"),
        ]

    def __str__(self):
        return f"{self.subscriber.username} — {self.usage_date} ({self.total_gb:.2f} GB)"

    @property
    def usage_percent(self) -> float:
        """Calculate usage as percentage of quota."""
        if not self.quota_limit_gb or self.quota_limit_gb == 0:
            return 0.0
        return (self.total_gb / self.quota_limit_gb) * 100

    @property
    def remaining_gb(self) -> float:
        """Calculate remaining quota."""
        if not self.quota_limit_gb:
            return float('inf')
        return max(0.0, self.quota_limit_gb - self.total_gb)

    def save(self, *args, **kwargs):
        """Recalculate derived fields before saving."""
        self.total_gb = self.upload_gb + self.download_gb
        self.is_exceeded = bool(
            self.quota_limit_gb and self.total_gb > self.quota_limit_gb
        )
        super().save(*args, **kwargs)
