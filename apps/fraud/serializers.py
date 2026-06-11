"""
apps/fraud/serializers.py
--------------------------
Serializers for fraud detection and alert management.
"""

from rest_framework import serializers

from .models import FraudRule, FraudAlert


class FraudRuleSerializer(serializers.ModelSerializer):
    """Serializer for fraud detection rules."""

    class Meta:
        model = FraudRule
        fields = [
            'id',
            'name',
            'rule_type',
            'description',
            'is_enabled',
            'severity',
            'threshold_value',
            'time_window_minutes',
            'auto_trigger_action',
            'require_admin_review',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FraudAlertListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for fraud alert listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    rule_name = serializers.CharField(
        source='rule.name',
        read_only=True,
    )

    class Meta:
        model = FraudAlert
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'rule_name',
            'status',
            'severity',
            'description',
            'created_at',
            'resolved_at',
        ]


class FraudAlertDetailSerializer(serializers.ModelSerializer):
    """Full serializer for fraud alert details."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    subscriber_phone = serializers.CharField(
        source='subscriber.phone_number',
        read_only=True,
    )
    rule = FraudRuleSerializer(read_only=True)
    investigated_by_name = serializers.CharField(
        source='investigated_by.full_name',
        read_only=True,
    )

    class Meta:
        model = FraudAlert
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'subscriber_phone',
            'rule',
            'status',
            'severity',
            'evidence',
            'description',
            'investigated_by',
            'investigated_by_name',
            'resolution',
            'investigation_notes',
            'action_taken',
            'resolved_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FraudAlertUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating fraud alert status."""

    class Meta:
        model = FraudAlert
        fields = [
            'status',
            'resolution',
            'investigation_notes',
            'action_taken',
        ]

    def validate(self, data):
        """Ensure resolution provided when resolved."""
        status = data.get('status') or self.instance.status
        if status == FraudAlert.Status.RESOLVED and not data.get('resolution'):
            raise serializers.ValidationError(
                {'resolution': 'Resolution type is required when closing an alert.'}
            )
        return data
