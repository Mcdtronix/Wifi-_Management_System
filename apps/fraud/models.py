"""
apps/fraud/models.py
--------------------
Fraud detection rules, alerts, and case management.
Identifies credential sharing, multiple MAC attempts, suspicious patterns.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from utils.mixins import BaseModel


class FraudRule(BaseModel):
    """
    Configurable fraud detection rule.
    Admins can tune thresholds and enable/disable specific checks.
    """

    class RuleType(models.TextChoices):
        MULTIPLE_MAC = "multiple_mac", _("Multiple MAC Addresses")
        CONCURRENT_SESSIONS = "concurrent_sessions", _("Concurrent Sessions")
        REPEATED_LOGIN_FAILURES = "repeated_login_failures", _("Repeated Login Failures")
        GEOGRAPHIC_ANOMALY = "geographic_anomaly", _("Geographic Anomaly")
        EXCESSIVE_DATA = "excessive_data", _("Excessive Data Consumption")
        SUSPICIOUS_DEVICE_CHANGE = "suspicious_device_change", _("Suspicious Device Change")
        THROTTLED_BYPASS = "throttled_bypass", _("Throttle Bypass Attempt")
        CREDENTIAL_SHARING = "credential_sharing", _("Credential Sharing")

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name=_("Rule Name"),
    )
    rule_type = models.CharField(
        max_length=50,
        choices=RuleType.choices,
        db_index=True,
        verbose_name=_("Rule Type"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_enabled = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Enabled"),
    )
    severity = models.PositiveSmallIntegerField(
        choices=[
            (1, _("Low")),
            (2, _("Medium")),
            (3, _("High")),
            (4, _("Critical")),
        ],
        default=2,
        verbose_name=_("Severity Level"),
    )
    
    # Thresholds (type-specific)
    threshold_value = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Threshold Value"),
        help_text=_("Context-dependent: count, time minutes, GB, etc."),
    )
    time_window_minutes = models.PositiveSmallIntegerField(
        default=60,
        verbose_name=_("Time Window (minutes)"),
        help_text=_("Window for detecting pattern."),
    )
    
    # Action
    auto_trigger_action = models.CharField(
        max_length=50,
        choices=[
            ("alert", _("Alert only")),
            ("throttle", _("Throttle speed")),
            ("block", _("Block access")),
            ("suspend", _("Suspend account")),
        ],
        default="alert",
        verbose_name=_("Auto-Trigger Action"),
    )
    require_admin_review = models.BooleanField(
        default=True,
        verbose_name=_("Require Admin Review"),
        help_text=_("If true, action taken only after manual approval."),
    )

    class Meta:
        db_table = "fraud_rule"
        ordering = ["severity", "name"]
        verbose_name = _("Fraud Detection Rule")
        verbose_name_plural = _("Fraud Detection Rules")

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class FraudAlert(BaseModel):
    """
    Active fraud alert triggered when rule condition is met.
    Tracks investigation status and admin actions.
    """

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        INVESTIGATING = "investigating", _("Under Investigation")
        RESOLVED = "resolved", _("Resolved")
        FALSE_POSITIVE = "false_positive", _("False Positive")
        WHITELISTED = "whitelisted", _("Whitelisted")

    class Resolution(models.TextChoices):
        BENIGN = "benign", _("Benign Behavior")
        USER_ERROR = "user_error", _("User Error")
        ACCOUNT_COMPROMISED = "account_compromised", _("Account Compromised")
        SYSTEM_ISSUE = "system_issue", _("System Issue")
        POLICY_ADJUSTMENT = "policy_adjustment", _("Policy Needs Adjustment")

    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="fraud_alerts",
        verbose_name=_("Subscriber"),
    )
    rule = models.ForeignKey(
        FraudRule,
        on_delete=models.PROTECT,
        related_name="alerts",
        verbose_name=_("Triggered Rule"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
        verbose_name=_("Status"),
    )
    severity = models.PositiveSmallIntegerField(
        choices=[
            (1, _("Low")),
            (2, _("Medium")),
            (3, _("High")),
            (4, _("Critical")),
        ],
        verbose_name=_("Severity"),
    )
    
    # Detection details
    evidence = models.JSONField(
        default=dict,
        verbose_name=_("Evidence"),
        help_text=_("Structured data supporting the alert (IPs, MACs, timestamps, etc.)."),
    )
    description = models.TextField(verbose_name=_("Alert Description"))
    
    # Admin response
    investigated_by = models.ForeignKey(
        "accounts.AdminUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="investigated_fraud_alerts",
        verbose_name=_("Investigated By"),
    )
    resolution = models.CharField(
        max_length=50,
        choices=Resolution.choices,
        null=True,
        blank=True,
        verbose_name=_("Resolution"),
    )
    investigation_notes = models.TextField(
        blank=True,
        verbose_name=_("Investigation Notes"),
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Resolved At"),
    )
    
    # Action taken
    action_taken = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Action Taken"),
        help_text=_("E.g. 'throttled', 'suspended', 'device_revoked'."),
    )

    class Meta:
        db_table = "fraud_alert"
        ordering = ["-created_at"]
        verbose_name = _("Fraud Alert")
        verbose_name_plural = _("Fraud Alerts")
        indexes = [
            models.Index(fields=["subscriber", "-created_at"], name="idx_fraud_sub_date"),
            models.Index(fields=["status"], name="idx_fraud_status"),
            models.Index(fields=["severity"], name="idx_fraud_severity"),
        ]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.subscriber.username} — {self.rule.name}"
