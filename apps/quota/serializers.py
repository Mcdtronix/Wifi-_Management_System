"""
apps/quota/serializers.py
--------------------------
Serializers for daily quota policies and usage tracking.
"""

from rest_framework import serializers

from .models import QuotaPolicy, DailyQuotaUsage


class QuotaPolicySerializer(serializers.ModelSerializer):
    """Serializer for quota policy management."""

    class Meta:
        model = QuotaPolicy
        fields = [
            'id',
            'name',
            'daily_quota_gb',
            'warning_threshold_percent',
            'soft_limit_percent',
            'throttle_speed_mbps',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class DailyQuotaUsageSerializer(serializers.ModelSerializer):
    """Serializer for daily quota usage tracking."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    usage_percent = serializers.FloatField(read_only=True)
    remaining_gb = serializers.FloatField(read_only=True)

    class Meta:
        model = DailyQuotaUsage
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'usage_date',
            'upload_gb',
            'download_gb',
            'total_gb',
            'quota_limit_gb',
            'usage_percent',
            'remaining_gb',
            'is_exceeded',
            'throttled',
            'blocked',
            'warning_sent_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'usage_percent',
            'remaining_gb',
            'created_at',
            'updated_at',
        ]


class DailyQuotaUsageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for quota usage listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    usage_percent = serializers.FloatField(read_only=True)

    class Meta:
        model = DailyQuotaUsage
        fields = [
            'id',
            'subscriber_name',
            'usage_date',
            'total_gb',
            'quota_limit_gb',
            'usage_percent',
            'is_exceeded',
            'blocked',
        ]
