"""
apps/subscribers/serializers.py
--------------------------------
Serializers for subscriber (customer) accounts.
"""

from rest_framework import serializers

from .models import Subscriber


class SubscriberListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for subscriber listings."""

    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True,
    )

    class Meta:
        model = Subscriber
        fields = [
            'id',
            'full_name',
            'username',
            'phone_number',
            'email',
            'account_status',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = [
            'created_at',
        ]


class SubscriberSummarySerializer(serializers.ModelSerializer):
    """
    Flat summary serializer mapping the backend Subscriber model to the exact
    camelCase structure expected by the frontend table mock.
    Prevents heavy client-side data manipulation.
    """
    fullName = serializers.CharField(source='full_name', read_only=True)
    phone = serializers.CharField(source='phone_number', read_only=True)
    status = serializers.CharField(source='account_status', read_only=True)
    
    plan = serializers.SerializerMethodField()
    expiresAt = serializers.SerializerMethodField()
    deviceName = serializers.SerializerMethodField()
    macAddress = serializers.SerializerMethodField()
    usedGb = serializers.SerializerMethodField()
    quotaGb = serializers.SerializerMethodField()
    speedMbps = serializers.SerializerMethodField()

    class Meta:
        model = Subscriber
        fields = [
            'id', 'fullName', 'username', 'phone', 'status',
            'plan', 'expiresAt', 'deviceName', 'macAddress', 'usedGb', 'quotaGb', 'speedMbps'
        ]

    def get_plan(self, obj):
        subs = getattr(obj, 'active_subs', [])
        return subs[0].plan.name if subs else "No Active Plan"

    def get_expiresAt(self, obj):
        subs = getattr(obj, 'active_subs', [])
        return subs[0].expires_at.date().isoformat() if subs and subs[0].expires_at else None

    def get_deviceName(self, obj):
        devices = getattr(obj, 'active_devices', [])
        return devices[0].device_name if devices else "Unknown Device"

    def get_macAddress(self, obj):
        devices = getattr(obj, 'active_devices', [])
        return devices[0].mac_address if devices else "Pending registration"

    def get_usedGb(self, obj):
        usage = getattr(obj, 'todays_usage', [])
        return round(usage[0].total_gb, 2) if usage else 0.0

    def get_quotaGb(self, obj):
        usage = getattr(obj, 'todays_usage', [])
        if usage and usage[0].quota_limit_gb:
            return float(usage[0].quota_limit_gb)
        return None

    def get_speedMbps(self, obj):
        subs = getattr(obj, 'active_subs', [])
        if subs and subs[0].plan and subs[0].plan.bandwidth_profile:
            return subs[0].plan.bandwidth_profile.download_mbps
        return None


class SubscriberDetailSerializer(serializers.ModelSerializer):
    """Full serializer for subscriber details."""

    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True,
    )
    created_by_email = serializers.CharField(
        source='created_by.email',
        read_only=True,
    )

    class Meta:
        model = Subscriber
        fields = [
            'id',
            'full_name',
            'username',
            'phone_number',
            'email',
            'national_id',
            'account_status',
            'suspension_reason',
            'created_by',
            'created_by_name',
            'created_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'radius_password',
            'created_by',
            'created_at',
            'updated_at',
        ]


class SubscriberCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new subscribers."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Subscriber
        fields = [
            'id',
            'full_name',
            'username',
            'phone_number',
            'email',
            'national_id',
            'password',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        """Create new subscriber with hashed RADIUS password."""
        password = validated_data.pop('password')
        subscriber = Subscriber(**validated_data)
        subscriber.set_radius_password(password)
        subscriber.save()
        return subscriber


class SubscriberUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating subscriber details."""

    class Meta:
        model = Subscriber
        fields = [
            'full_name',
            'email',
            'national_id',
            'account_status',
            'suspension_reason',
        ]

    def validate(self, data):
        """Ensure suspension_reason is provided when suspending account."""
        status = data.get('account_status')
        if status in ['suspended', 'banned']:
            if not data.get('suspension_reason'):
                raise serializers.ValidationError(
                    {'suspension_reason': 'Suspension reason is required when suspending or banning.'}
                )
        return data


class SubscriberResetPasswordSerializer(serializers.Serializer):
    """Serializer for resetting subscriber RADIUS password."""

    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        """Ensure passwords match."""
        if data.get('new_password') != data.get('confirm_password'):
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'}
            )
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting an OTP password reset."""

    username = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=20)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming OTP and setting new password."""

    username = serializers.CharField(max_length=150)
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        """Ensure passwords match."""
        if data.get('new_password') != data.get('confirm_password'):
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'}
            )
        return data

class SubscriberLoginSerializer(serializers.Serializer):
    """Serializer for authenticating a subscriber."""

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    mac_address = serializers.CharField(max_length=17, required=False, allow_blank=True)
    device_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
