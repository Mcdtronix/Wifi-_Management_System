"""
apps/accounting/serializers.py
-------------------------------
Serializers for RADIUS accounting records and session tracking.
"""

from rest_framework import serializers

from .models import RadiusAccounting, Session


class RadiusAccountingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for RADIUS accounting listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    total_bytes = serializers.IntegerField(read_only=True)

    class Meta:
        model = RadiusAccounting
        fields = [
            'id',
            'username',
            'subscriber',
            'subscriber_name',
            'acctstarttime',
            'acctstoptime',
            'acctstatustype',
            'acctinputoctets',
            'acctoutputoctets',
            'total_bytes',
            'acctsessiontime',
        ]


class RadiusAccountingDetailSerializer(serializers.ModelSerializer):
    """Full serializer for RADIUS accounting details."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    total_bytes = serializers.IntegerField(read_only=True)

    class Meta:
        model = RadiusAccounting
        fields = [
            'id',
            'acctuniqueid',
            'username',
            'realm',
            'subscriber',
            'subscriber_name',
            'nasipaddress',
            'nasportid',
            'nasporttype',
            'acctstarttime',
            'acctstoptime',
            'acctsessiontime',
            'acctstatustype',
            'acctauthentic',
            'acctinputoctets',
            'acctoutputoctets',
            'total_bytes',
            'calledstationid',
            'callingstationid',
            'framedipaddress',
            'acctterminatecause',
            'servicetype',
            'framedprotocol',
            'connectinfo_start',
            'connectinfo_stop',
        ]
        read_only_fields = fields


class SessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for session listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    total_bytes = serializers.SerializerMethodField()
    upload_mb = serializers.SerializerMethodField()
    download_mb = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'mac_address',
            'state',
            'started_at',
            'ended_at',
            'duration_seconds',
            'upload_bytes',
            'download_bytes',
            'upload_mb',
            'download_mb',
            'total_bytes',
        ]

    def get_total_bytes(self, obj):
        """Calculate total bytes used."""
        return obj.upload_bytes + obj.download_bytes

    def get_upload_mb(self, obj):
        """Convert upload bytes to MB."""
        return round(obj.upload_bytes / (1024 ** 2), 2)

    def get_download_mb(self, obj):
        """Convert download bytes to MB."""
        return round(obj.download_bytes / (1024 ** 2), 2)


class SessionDetailSerializer(serializers.ModelSerializer):
    """Full serializer for session details."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    subscriber_phone = serializers.CharField(
        source='subscriber.phone_number',
        read_only=True,
    )
    total_bytes = serializers.SerializerMethodField()
    upload_mb = serializers.SerializerMethodField()
    download_mb = serializers.SerializerMethodField()
    upload_gb = serializers.SerializerMethodField()
    download_gb = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'subscriber_phone',
            'radius_record',
            'mac_address',
            'client_ip',
            'state',
            'started_at',
            'ended_at',
            'duration_seconds',
            'upload_bytes',
            'download_bytes',
            'upload_mb',
            'download_mb',
            'upload_gb',
            'download_gb',
            'total_bytes',
            'terminate_cause',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_total_bytes(self, obj):
        """Calculate total bytes used."""
        return obj.upload_bytes + obj.download_bytes

    def get_upload_mb(self, obj):
        """Convert upload bytes to MB."""
        return round(obj.upload_bytes / (1024 ** 2), 2)

    def get_download_mb(self, obj):
        """Convert download bytes to MB."""
        return round(obj.download_bytes / (1024 ** 2), 2)

    def get_upload_gb(self, obj):
        """Convert upload bytes to GB."""
        return round(obj.upload_bytes / (1024 ** 3), 2)

    def get_download_gb(self, obj):
        """Convert download bytes to GB."""
        return round(obj.download_bytes / (1024 ** 3), 2)


class SessionFilterSerializer(serializers.Serializer):
    """Serializer for filtering sessions."""

    subscriber_id = serializers.UUIDField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    state = serializers.ChoiceField(
        choices=Session.SessionState.choices,
        required=False,
    )
