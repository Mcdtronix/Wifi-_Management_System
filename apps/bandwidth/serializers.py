"""
apps/bandwidth/serializers.py
------------------------------
Serializers for bandwidth profiles and speed tiers.
"""

from rest_framework import serializers

from .models import BandwidthProfile


class BandwidthProfileListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for bandwidth profile listings."""

    class Meta:
        model = BandwidthProfile
        fields = [
            'id',
            'name',
            'tier',
            'download_mbps',
            'upload_mbps',
            'is_active',
        ]


class BandwidthProfileDetailSerializer(serializers.ModelSerializer):
    """Full serializer for bandwidth profile details."""

    download_bps = serializers.IntegerField(read_only=True)
    upload_bps = serializers.IntegerField(read_only=True)

    class Meta:
        model = BandwidthProfile
        fields = [
            'id',
            'name',
            'tier',
            'download_mbps',
            'upload_mbps',
            'download_bps',
            'upload_bps',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'download_bps',
            'upload_bps',
            'created_at',
            'updated_at',
        ]


class BandwidthProfileCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating bandwidth profiles."""

    class Meta:
        model = BandwidthProfile
        fields = [
            'name',
            'tier',
            'download_mbps',
            'upload_mbps',
            'is_active',
        ]

    def validate(self, data):
        """Validate bandwidth profile constraints."""
        download = data.get('download_mbps')
        upload = data.get('upload_mbps')

        if download and upload and upload > download:
            raise serializers.ValidationError(
                {'upload_mbps': 'Upload speed should not exceed download speed.'}
            )

        return data
