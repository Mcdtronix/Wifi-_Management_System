"""
apps/captive_portal/serializers.py
-----------------------------------
Serializers for captive portal session and configuration management.
"""

from rest_framework import serializers

from .models import PortalConfig, PortalSession


class PortalConfigSerializer(serializers.ModelSerializer):
    """Serializer for captive portal configuration."""

    class Meta:
        model = PortalConfig
        fields = [
            'id',
            'site_name',
            'site_url',
            'logo_url',
            'header_text',
            'footer_text',
            'primary_color',
            'secondary_color',
            'session_timeout_minutes',
            'allow_remember_me',
            'require_email',
            'require_phone',
            'show_terms',
            'terms_text',
            'terms_version',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class PortalSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for portal session listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )

    class Meta:
        model = PortalSession
        fields = [
            'id',
            'subscriber_name',
            'ip_address',
            'mac_address',
            'is_active',
            'logged_in_at',
            'last_activity_at',
            'logged_out_at',
        ]


class PortalSessionDetailSerializer(serializers.ModelSerializer):
    """Full serializer for portal session details."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    subscriber_username = serializers.CharField(
        source='subscriber.username',
        read_only=True,
    )

    class Meta:
        model = PortalSession
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'subscriber_username',
            'session_key',
            'ip_address',
            'user_agent',
            'mac_address',
            'is_active',
            'logged_in_at',
            'last_activity_at',
            'logged_out_at',
            'logout_reason',
            'created_at',
        ]
        read_only_fields = fields


class PortalLoginSerializer(serializers.Serializer):
    """Serializer for captive portal login."""

    username = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True, min_length=1)
    mac_address = serializers.CharField(max_length=17, required=False)
    remember_me = serializers.BooleanField(default=False, required=False)


class PortalStatusSerializer(serializers.Serializer):
    """Serializer for portal user status check."""

    is_authenticated = serializers.BooleanField()
    subscriber_id = serializers.UUIDField(required=False)
    username = serializers.CharField(max_length=32, required=False)
    account_status = serializers.CharField(max_length=20, required=False)
    subscription_active = serializers.BooleanField(required=False)
    time_remaining_hours = serializers.IntegerField(required=False)
