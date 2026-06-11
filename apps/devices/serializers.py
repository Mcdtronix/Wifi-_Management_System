"""
apps/devices/serializers.py
----------------------------
Serializers for device registration and device change requests.
"""

from rest_framework import serializers

from .models import Device, DeviceChangeRequest


class DeviceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for device listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )

    class Meta:
        model = Device
        fields = [
            'id',
            'mac_address',
            'device_name',
            'status',
            'is_primary',
            'subscriber',
            'subscriber_name',
            'first_seen_at',
            'last_seen_at',
        ]


class DeviceDetailSerializer(serializers.ModelSerializer):
    """Full serializer for device details."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    subscriber_username = serializers.CharField(
        source='subscriber.username',
        read_only=True,
    )
    registered_by_name = serializers.CharField(
        source='registered_by.full_name',
        read_only=True,
    )

    class Meta:
        model = Device
        fields = [
            'id',
            'mac_address',
            'device_name',
            'status',
            'is_primary',
            'subscriber',
            'subscriber_name',
            'subscriber_username',
            'first_seen_at',
            'last_seen_at',
            'registered_by',
            'registered_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'first_seen_at',
            'last_seen_at',
            'created_at',
            'updated_at',
        ]


class DeviceCreateSerializer(serializers.ModelSerializer):
    """Serializer for registering new devices."""

    class Meta:
        model = Device
        fields = [
            'mac_address',
            'device_name',
            'subscriber',
        ]


class DeviceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating device information."""

    class Meta:
        model = Device
        fields = [
            'device_name',
            'status',
        ]


class DeviceChangeRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for device change request listings."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    current_mac = serializers.CharField(
        source='current_device.mac_address',
        read_only=True,
    )

    class Meta:
        model = DeviceChangeRequest
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'current_mac',
            'new_mac_address',
            'reason',
            'status',
            'created_at',
        ]


class DeviceChangeRequestDetailSerializer(serializers.ModelSerializer):
    """Full serializer for device change request details."""

    subscriber_name = serializers.CharField(
        source='subscriber.full_name',
        read_only=True,
    )
    subscriber_phone = serializers.CharField(
        source='subscriber.phone_number',
        read_only=True,
    )
    current_mac = serializers.CharField(
        source='current_device.mac_address',
        read_only=True,
    )
    approved_by_name = serializers.CharField(
        source='approved_by.full_name',
        read_only=True,
    )

    class Meta:
        model = DeviceChangeRequest
        fields = [
            'id',
            'subscriber',
            'subscriber_name',
            'subscriber_phone',
            'current_device',
            'current_mac',
            'new_mac_address',
            'reason',
            'status',
            'approval_comment',
            'approved_by',
            'approved_by_name',
            'approved_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'status',
            'approved_by',
            'approved_at',
            'created_at',
            'updated_at',
        ]


class DeviceChangeRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating device change requests."""

    class Meta:
        model = DeviceChangeRequest
        fields = [
            'new_mac_address',
            'reason',
        ]


class DeviceChangeRequestApprovalSerializer(serializers.ModelSerializer):
    """Serializer for approving/rejecting device change requests."""

    class Meta:
        model = DeviceChangeRequest
        fields = [
            'status',
            'approval_comment',
        ]

    def validate_status(self, value):
        """Ensure only valid approval statuses."""
        if value not in [DeviceChangeRequest.RequestStatus.APPROVED, DeviceChangeRequest.RequestStatus.REJECTED]:
            raise serializers.ValidationError(
                f'Status must be {DeviceChangeRequest.RequestStatus.APPROVED} or {DeviceChangeRequest.RequestStatus.REJECTED}.'
            )
        return value
