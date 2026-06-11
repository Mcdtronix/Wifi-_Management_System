"""
apps/radius/serializers.py
---------------------------
Serializers for FreeRADIUS integration and configuration.
"""

from rest_framework import serializers

from .models import RadiusReplyAttribute, RadiusConfig


class RadiusReplyAttributeSerializer(serializers.ModelSerializer):
    """Serializer for RADIUS reply attribute configuration."""

    class Meta:
        model = RadiusReplyAttribute
        fields = [
            'id',
            'name',
            'attribute_type',
            'value_template',
            'operator',
            'is_reply',
            'is_enabled',
            'priority',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class RadiusReplyAttributeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for attribute listings."""

    class Meta:
        model = RadiusReplyAttribute
        fields = [
            'id',
            'name',
            'attribute_type',
            'operator',
            'is_enabled',
            'priority',
        ]


class RadiusConfigSerializer(serializers.ModelSerializer):
    """Serializer for FreeRADIUS server configuration."""

    class Meta:
        model = RadiusConfig
        fields = [
            'id',
            'server_host',
            'server_port',
            'accounting_port',
            'auth_timeout_seconds',
            'max_retries',
            'accounting_enabled',
            'interim_update_interval',
            'allow_concurrent_sessions',
            'max_sessions_per_user',
            'session_timeout_seconds',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'shared_secret': {'write_only': True},
        }

    def validate_server_host(self, value):
        """Validate RADIUS server hostname/IP."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('Server host cannot be empty.')
        return value

    def validate_server_port(self, value):
        """Validate port number."""
        if not 1 <= value <= 65535:
            raise serializers.ValidationError('Port must be between 1 and 65535.')
        return value

    def validate_max_sessions_per_user(self, value):
        """Validate session limit."""
        if value < 1:
            raise serializers.ValidationError('Max sessions must be at least 1.')
        return value


class RadiusHealthCheckSerializer(serializers.Serializer):
    """Serializer for RADIUS server health check results."""

    is_reachable = serializers.BooleanField()
    response_time_ms = serializers.FloatField()
    error_message = serializers.CharField(required=False, allow_blank=True)
