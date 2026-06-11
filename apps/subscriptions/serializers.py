"""
apps/subscriptions/serializers.py
----------------------------------
Serializers for subscription plans and active subscriptions.
"""

from rest_framework import serializers

from .models import Plan, Subscription
from apps.bandwidth.models import BandwidthProfile
from apps.quota.models import QuotaPolicy


class BandwidthProfileNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for bandwidth profiles."""

    class Meta:
        model = BandwidthProfile
        fields = [
            'id',
            'name',
            'tier',
            'download_mbps',
            'upload_mbps',
        ]
        read_only_fields = fields


class QuotaPolicyNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for quota policies."""

    class Meta:
        model = QuotaPolicy
        fields = [
            'id',
            'name',
            'daily_quota_gb',
        ]
        read_only_fields = fields


class PlanListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for plan listings.
    Flattened to match the exact camelCase structure expected by the frontend.
    """

    price = serializers.DecimalField(
        source='price_usd',
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    durationDays = serializers.IntegerField(
        source='duration_days',
        read_only=True,
    )
    bandwidthMbps = serializers.IntegerField(
        source='bandwidth_profile.download_mbps',
        read_only=True,
    )
    quotaGb = serializers.DecimalField(
        source='quota_policy.daily_quota_gb',
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Plan
        fields = [
            'id',
            'name',
            'price',
            'durationDays',
            'bandwidthMbps',
            'quotaGb',
            'is_active',
        ]


class PlanDetailSerializer(serializers.ModelSerializer):
    """Full serializer for plan details."""

    bandwidth_profile = BandwidthProfileNestedSerializer(read_only=True)
    bandwidth_profile_id = serializers.PrimaryKeyRelatedField(
        queryset=BandwidthProfile.objects.all(),
        write_only=True,
        required=False,
        source='bandwidth_profile',
    )
    quota_policy = QuotaPolicyNestedSerializer(read_only=True)
    quota_policy_id = serializers.PrimaryKeyRelatedField(
        queryset=QuotaPolicy.objects.all(),
        write_only=True,
        required=False,
        source='quota_policy',
    )

    class Meta:
        model = Plan
        fields = [
            'id',
            'name',
            'plan_type',
            'duration_days',
            'price_usd',
            'bandwidth_profile',
            'bandwidth_profile_id',
            'quota_policy',
            'quota_policy_id',
            'is_active',
            'description',
            'grace_period_hours',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'created_at',
            'updated_at',
        ]


class PlanCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating plans."""

    class Meta:
        model = Plan
        fields = [
            'name',
            'plan_type',
            'duration_days',
            'price_usd',
            'bandwidth_profile',
            'quota_policy',
            'is_active',
            'description',
            'grace_period_hours',
        ]


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for subscription listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    plan_name = serializers.CharField(
        source='plan.name',
        read_only=True,
    )

    class Meta:
        model = Subscription
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'plan',
            'plan_name',
            'status',
            'activated_at',
            'expires_at',
            'created_at',
        ]


class SubscriptionDetailSerializer(serializers.ModelSerializer):
    """Full serializer for subscription details."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    plan = PlanDetailSerializer(read_only=True)
    activated_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True,
    )

    class Meta:
        model = Subscription
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'plan',
            'status',
            'activated_at',
            'expires_at',
            'grace_ends_at',
            'created_by',
            'activated_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'status',
            'activated_at',
            'expires_at',
            'grace_ends_at',
            'created_by',
            'created_at',
            'updated_at',
        ]


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/activating subscriptions."""

    class Meta:
        model = Subscription
        fields = [
            'subscriber',
            'plan',
        ]


class SubscriptionRenewalSerializer(serializers.Serializer):
    """Serializer for renewing subscriptions."""

    extend_days = serializers.IntegerField(
        min_value=1,
        max_value=365,
        help_text='Number of days to extend the subscription.',
    )

    def validate_extend_days(self, value):
        """Validate extension period."""
        if value > 365:
            raise serializers.ValidationError('Cannot extend by more than 365 days at once.')
        return value
