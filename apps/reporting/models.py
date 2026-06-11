"""
apps/reporting/models.py
------------------------
Analytics, reporting, and dashboard metrics aggregation.
Pre-computed statistics for fast dashboard loading.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.mixins import BaseModel


class DashboardMetrics(BaseModel):
    """
    Aggregated daily metrics for admin dashboard.
    Pre-computed snapshots for fast retrieval.
    """

    metrics_date = models.DateField(
        unique=True,
        db_index=True,
        verbose_name=_("Metrics Date"),
    )
    
    # Subscriber metrics
    total_subscribers = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Subscribers"),
    )
    active_subscribers = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Active Subscribers"),
    )
    expired_subscribers = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Expired Subscribers"),
    )
    suspended_subscribers = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Suspended Subscribers"),
    )
    new_subscribers_today = models.PositiveIntegerField(
        default=0,
        verbose_name=_("New Today"),
    )
    churned_subscribers = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Churned (Expired)"),
    )
    
    # Session metrics
    online_now = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Online Now"),
    )
    sessions_today = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Sessions Today"),
    )
    avg_session_minutes = models.FloatField(
        default=0.0,
        verbose_name=_("Avg Session Duration (minutes)"),
    )
    
    # Traffic metrics
    total_upload_gb = models.FloatField(
        default=0.0,
        verbose_name=_("Total Upload (GB)"),
    )
    total_download_gb = models.FloatField(
        default=0.0,
        verbose_name=_("Total Download (GB)"),
    )
    total_traffic_gb = models.FloatField(
        default=0.0,
        verbose_name=_("Total Traffic (GB)"),
    )
    peak_hour = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Peak Hour (0-23)"),
    )
    
    # Quota metrics
    quota_exceeded_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Quota Exceeded"),
    )
    quota_warned_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Quota Warnings"),
    )
    
    # Revenue metrics
    revenue_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name=_("Revenue (USD)"),
    )
    new_plans_sold = models.PositiveIntegerField(
        default=0,
        verbose_name=_("New Plans Sold"),
    )
    renewals_today = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Renewals"),
    )
    vouchers_redeemed = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Vouchers Redeemed"),
    )
    
    # Error metrics
    failed_logins = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Failed Login Attempts"),
    )
    fraud_alerts = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Fraud Alerts Triggered"),
    )
    system_errors = models.PositiveIntegerField(
        default=0,
        verbose_name=_("System Errors"),
    )
    
    # Device metrics
    unique_devices = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Unique Devices"),
    )
    device_changes_requested = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Device Changes Requested"),
    )
    
    # Admin metrics
    admin_actions_today = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Admin Actions"),
    )

    class Meta:
        db_table = "reporting_dashboard_metrics"
        ordering = ["-metrics_date"]
        verbose_name = _("Dashboard Metrics")
        verbose_name_plural = _("Dashboard Metrics")

    def __str__(self):
        return f"Metrics for {self.metrics_date}"


class RevenueSummary(BaseModel):
    """
    Monthly revenue breakdown by plan type.
    Used for financial reporting and forecasting.
    """

    summary_date = models.DateField(
        verbose_name=_("Month (first day)"),
    )
    
    daily_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name=_("Daily Revenue"),
    )
    weekly_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name=_("Weekly Revenue"),
    )
    monthly_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name=_("Monthly Revenue"),
    )
    
    # By plan type
    daily_plan_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name=_("Daily Plans Revenue"),
    )
    weekly_plan_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name=_("Weekly Plans Revenue"),
    )
    monthly_plan_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name=_("Monthly Plans Revenue"),
    )
    custom_plan_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name=_("Custom Plans Revenue"),
    )
    
    # Transactions
    total_transactions = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Transactions"),
    )
    successful_transactions = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Successful Transactions"),
    )
    failed_transactions = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Failed Transactions"),
    )
    
    # Subscribers
    new_subscriptions = models.PositiveIntegerField(
        default=0,
        verbose_name=_("New Subscriptions"),
    )
    renewed_subscriptions = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Renewed Subscriptions"),
    )
    cancelled_subscriptions = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Cancelled Subscriptions"),
    )

    class Meta:
        db_table = "reporting_revenue_summary"
        ordering = ["-summary_date"]
        unique_together = [["summary_date"]]
        verbose_name = _("Revenue Summary")
        verbose_name_plural = _("Revenue Summaries")

    def __str__(self):
        return f"Revenue for {self.summary_date.strftime('%B %Y')}"


class SubscriberReport(BaseModel):
    """
    Individual subscriber usage and activity report.
    Generated periodically for user insights and billing.
    """

    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name=_("Subscriber"),
    )
    report_period_start = models.DateField(verbose_name=_("Period Start"))
    report_period_end = models.DateField(verbose_name=_("Period End"))
    
    # Activity
    sessions_count = models.PositiveIntegerField(default=0, verbose_name=_("Sessions"))
    total_session_hours = models.FloatField(default=0.0, verbose_name=_("Total Hours Online"))
    last_active_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Active"))
    
    # Usage
    upload_gb = models.FloatField(default=0.0, verbose_name=_("Upload (GB)"))
    download_gb = models.FloatField(default=0.0, verbose_name=_("Download (GB)"))
    total_gb = models.FloatField(default=0.0, verbose_name=_("Total (GB)"))
    quota_limit_gb = models.FloatField(null=True, blank=True, verbose_name=_("Quota Limit (GB)"))
    quota_usage_percent = models.FloatField(default=0.0, verbose_name=_("Quota Usage (%)"))
    
    # Subscription
    plans_active = models.PositiveIntegerField(default=0, verbose_name=_("Active Plans"))
    renewals_count = models.PositiveIntegerField(default=0, verbose_name=_("Renewals"))
    total_spent_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name=_("Total Spent"))
    
    # Alerts
    quota_warnings = models.PositiveIntegerField(default=0, verbose_name=_("Quota Warnings"))
    failed_logins = models.PositiveIntegerField(default=0, verbose_name=_("Failed Logins"))
    fraud_alerts = models.PositiveIntegerField(default=0, verbose_name=_("Fraud Alerts"))
    
    # Generated metadata
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Generated At"))
    is_sent = models.BooleanField(default=False, verbose_name=_("Sent to User"))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Sent At"))

    class Meta:
        db_table = "reporting_subscriber_report"
        ordering = ["-report_period_end"]
        verbose_name = _("Subscriber Report")
        verbose_name_plural = _("Subscriber Reports")

    def __str__(self):
        return f"{self.subscriber.username} — {self.report_period_start} to {self.report_period_end}"
