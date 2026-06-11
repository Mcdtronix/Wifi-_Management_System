"""
apps/reporting/serializers.py
------------------------------
Serializers for analytics, reporting, and dashboard metrics.
"""

from rest_framework import serializers

from .models import DashboardMetrics, RevenueSummary, SubscriberReport


class DashboardMetricsSerializer(serializers.ModelSerializer):
    """Serializer for admin dashboard metrics."""

    month_display = serializers.SerializerMethodField()

    class Meta:
        model = DashboardMetrics
        fields = [
            'id',
            'metrics_date',
            'month_display',
            'total_subscribers',
            'active_subscribers',
            'expired_subscribers',
            'suspended_subscribers',
            'new_subscribers_today',
            'online_now',
            'sessions_today',
            'avg_session_minutes',
            'total_traffic_gb',
            'peak_hour',
            'quota_exceeded_count',
            'revenue_usd',
            'failed_logins',
            'fraud_alerts',
        ]
        read_only_fields = fields

    def get_month_display(self, obj):
        """Format month display."""
        return obj.metrics_date.strftime('%B %Y')


class RevenueSummarySerializer(serializers.ModelSerializer):
    """Serializer for revenue reporting."""

    month_display = serializers.SerializerMethodField()
    mrr_usd = serializers.DecimalField(
        source='monthly_revenue',
        read_only=True,
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        model = RevenueSummary
        fields = [
            'id',
            'summary_date',
            'month_display',
            'daily_revenue',
            'weekly_revenue',
            'monthly_revenue',
            'mrr_usd',
            'daily_plan_revenue',
            'weekly_plan_revenue',
            'monthly_plan_revenue',
            'custom_plan_revenue',
            'total_transactions',
            'successful_transactions',
            'failed_transactions',
            'new_subscriptions',
            'renewed_subscriptions',
            'cancelled_subscriptions',
            'created_at',
        ]
        read_only_fields = fields

    def get_month_display(self, obj):
        """Format month display."""
        return obj.summary_date.strftime('%B %Y')


class RevenueSummaryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for revenue listings."""

    month_display = serializers.SerializerMethodField()

    class Meta:
        model = RevenueSummary
        fields = [
            'id',
            'summary_date',
            'month_display',
            'monthly_revenue',
            'total_transactions',
            'new_subscriptions',
            'renewed_subscriptions',
        ]

    def get_month_display(self, obj):
        """Format month display."""
        return obj.summary_date.strftime('%B %Y')


class SubscriberReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for subscriber report listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    period_display = serializers.SerializerMethodField()

    class Meta:
        model = SubscriberReport
        fields = [
            'id',
            'subscriber_name',
            'report_period_start',
            'report_period_end',
            'period_display',
            'total_gb',
            'total_spent_usd',
            'sessions_count',
            'generated_at',
            'is_sent',
        ]

    def get_period_display(self, obj):
        """Format period display."""
        return f"{obj.report_period_start} to {obj.report_period_end}"


class SubscriberReportDetailSerializer(serializers.ModelSerializer):
    """Full serializer for subscriber report details."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    subscriber_phone = serializers.CharField(
        source='subscriber.phone_number',
        read_only=True,
    )
    period_display = serializers.SerializerMethodField()

    class Meta:
        model = SubscriberReport
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'subscriber_phone',
            'report_period_start',
            'report_period_end',
            'period_display',
            'sessions_count',
            'total_session_hours',
            'last_active_at',
            'upload_gb',
            'download_gb',
            'total_gb',
            'quota_limit_gb',
            'quota_usage_percent',
            'plans_active',
            'renewals_count',
            'total_spent_usd',
            'quota_warnings',
            'failed_logins',
            'fraud_alerts',
            'generated_at',
            'is_sent',
            'sent_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_period_display(self, obj):
        """Format period display."""
        return f"{obj.report_period_start} to {obj.report_period_end}"


class ReportingFilterSerializer(serializers.Serializer):
    """Serializer for filtering reports."""

    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    subscriber_id = serializers.UUIDField(required=False)
    status_filter = serializers.ChoiceField(
        choices=['sent', 'not_sent', 'all'],
        required=False,
        default='all',
    )
    min_traffic_gb = serializers.FloatField(required=False, min_value=0)
    max_traffic_gb = serializers.FloatField(required=False, min_value=0)
