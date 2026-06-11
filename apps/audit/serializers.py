"""
apps/audit/serializers.py
--------------------------
Serializers for audit logging and compliance tracking.
"""

from rest_framework import serializers

from .models import AuditLog, AdminActivityLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for audit log entries."""

    actor_user_name = serializers.CharField(
        source='actor_user.full_name',
        read_only=True,
    )
    actor_subscriber_name = serializers.CharField(
        source='actor_subscriber.full_name',
        read_only=True,
    )
    object_type_name = serializers.CharField(
        source='content_type.model',
        read_only=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'action',
            'actor_user',
            'actor_user_name',
            'actor_subscriber',
            'actor_subscriber_name',
            'actor_ip',
            'object_type_name',
            'object_id',
            'description',
            'changes',
            'severity',
            'source',
            'metadata',
            'created_at',
        ]
        read_only_fields = fields


class AuditLogListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for audit log listings."""

    actor = serializers.SerializerMethodField()
    object_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'action',
            'actor',
            'actor_ip',
            'description',
            'severity',
            'object_display',
            'created_at',
        ]

    def get_actor(self, obj):
        """Get actor name."""
        if obj.actor_user:
            return obj.actor_user.full_name
        if obj.actor_subscriber:
            return obj.actor_subscriber.full_name
        return "System"

    def get_object_display(self, obj):
        """Get object type and ID."""
        if obj.content_type and obj.object_id:
            return f"{obj.content_type.model} #{obj.object_id}"
        return None


class AdminActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for administrative activity logs."""

    admin_name = serializers.CharField(
        source='admin.full_name',
        read_only=True,
    )
    target_user_name = serializers.CharField(
        source='target_user.full_name',
        read_only=True,
    )

    class Meta:
        model = AdminActivityLog
        fields = [
            'id',
            'admin',
            'admin_name',
            'action',
            'target_user',
            'target_user_name',
            'description',
            'ip_address',
            'user_agent',
            'affected_records_count',
            'created_at',
        ]
        read_only_fields = ['created_at']


class AdminActivityLogListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for admin activity listings."""

    admin_name = serializers.CharField(
        source='admin.full_name',
        read_only=True,
    )
    target_name = serializers.CharField(
        source='target_user.full_name',
        read_only=True,
    )

    class Meta:
        model = AdminActivityLog
        fields = [
            'id',
            'admin_name',
            'action',
            'target_name',
            'description',
            'affected_records_count',
            'created_at',
        ]
