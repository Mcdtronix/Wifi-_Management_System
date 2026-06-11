"""
apps/notifications/serializers.py
----------------------------------
Serializers for WhatsApp and multi-channel notifications.
"""

from rest_framework import serializers

from .models import NotificationTemplate, Notification, NotificationPreference


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification template management."""

    class Meta:
        model = NotificationTemplate
        fields = [
            'id',
            'name',
            'event_type',
            'channel',
            'subject',
            'body',
            'variables',
            'is_active',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for notification listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = [
            'id',
            'subscriber_name',
            'channel',
            'recipient',
            'status',
            'sent_at',
            'delivered_at',
            'created_at',
        ]


class NotificationDetailSerializer(serializers.ModelSerializer):
    """Full serializer for notification details."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    template_name = serializers.CharField(
        source='template.name',
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'template',
            'template_name',
            'channel',
            'recipient',
            'subject',
            'body',
            'status',
            'sent_at',
            'delivered_at',
            'external_id',
            'error_message',
            'retry_count',
            'event_type',
            'context_data',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'status',
            'sent_at',
            'delivered_at',
            'external_id',
            'error_message',
            'retry_count',
            'created_at',
            'updated_at',
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for subscriber notification preferences."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )

    class Meta:
        model = NotificationPreference
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'receive_whatsapp',
            'receive_sms',
            'receive_email',
            'receive_expiry_warnings',
            'receive_quota_warnings',
            'receive_security_alerts',
            'quiet_hours_start',
            'quiet_hours_end',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for sending bulk notifications."""

    event_type = serializers.ChoiceField(
        choices=NotificationTemplate.EventType.choices,
    )
    channel = serializers.ChoiceField(
        choices=NotificationTemplate.Channel.choices,
        required=False,
    )
    subscriber_filter = serializers.JSONField(
        required=False,
        help_text='Query filter to select subscribers.',
    )
    context_data = serializers.JSONField(
        required=False,
        help_text='Template variables.',
    )
    recipient_count = serializers.IntegerField(read_only=True)
