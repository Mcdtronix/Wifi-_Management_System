"""
apps/vouchers/serializers.py
-----------------------------
Serializers for voucher batches and individual voucher codes.
"""

from rest_framework import serializers

from .models import VoucherBatch, Voucher


class VoucherBatchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for voucher batch listings."""

    plan_name = serializers.CharField(
        source='plan.name',
        read_only=True,
    )
    generated_by_name = serializers.CharField(
        source='generated_by.full_name',
        read_only=True,
    )
    redeemed_count = serializers.SerializerMethodField()
    voided_count = serializers.SerializerMethodField()
    unused_count = serializers.SerializerMethodField()

    class Meta:
        model = VoucherBatch
        fields = [
            'id',
            'name',
            'plan',
            'plan_name',
            'quantity',
            'redeemed_count',
            'voided_count',
            'unused_count',
            'valid_from',
            'valid_until',
            'generated_by_name',
            'created_at',
        ]

    def get_redeemed_count(self, obj):
        """Count redeemed vouchers in batch."""
        return obj.vouchers.filter(status='redeemed').count()

    def get_voided_count(self, obj):
        """Count voided vouchers in batch."""
        return obj.vouchers.filter(status='voided').count()

    def get_unused_count(self, obj):
        """Count unused vouchers in batch."""
        return obj.vouchers.filter(status='unused').count()


class VoucherBatchDetailSerializer(serializers.ModelSerializer):
    """Full serializer for voucher batch details."""

    plan = serializers.StringRelatedField(read_only=True)
    generated_by_name = serializers.CharField(
        source='generated_by.full_name',
        read_only=True,
    )
    redeemed_count = serializers.SerializerMethodField()
    voided_count = serializers.SerializerMethodField()
    unused_count = serializers.SerializerMethodField()

    class Meta:
        model = VoucherBatch
        fields = [
            'id',
            'name',
            'plan',
            'quantity',
            'valid_from',
            'valid_until',
            'generated_by',
            'generated_by_name',
            'notes',
            'redeemed_count',
            'voided_count',
            'unused_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'created_at',
            'updated_at',
        ]


class VoucherBatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating voucher batches."""

    class Meta:
        model = VoucherBatch
        fields = [
            'name',
            'plan',
            'quantity',
            'valid_from',
            'valid_until',
            'notes',
        ]


class VoucherListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for voucher listings.
    Flattened to match the exact frontend mock structure.
    """

    batch_name = serializers.CharField(
        source='batch.name',
        read_only=True,
    )
    plan = serializers.CharField(
        source='batch.plan.name',
        read_only=True,
    )
    createdAt = serializers.DateTimeField(
        source='created_at',
        read_only=True,
    )

    class Meta:
        model = Voucher
        fields = [
            'id',
            'code',
            'batch_name',
            'plan',
            'status',
            'createdAt',
        ]


class VoucherDetailSerializer(serializers.ModelSerializer):
    """Full serializer for voucher details."""

    batch_name = serializers.CharField(
        source='batch.name',
        read_only=True,
    )
    plan = serializers.StringRelatedField(
        source='batch.plan',
        read_only=True,
    )
    redeemed_by_name = serializers.CharField(
        source='redeemed_by.full_name',
        read_only=True,
    )

    class Meta:
        model = Voucher
        fields = [
            'id',
            'code',
            'batch',
            'batch_name',
            'plan',
            'status',
            'redeemed_by',
            'redeemed_by_name',
            'redeemed_at',
            'expired_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'code',
            'status',
            'redeemed_by',
            'redeemed_at',
            'expired_at',
            'created_at',
            'updated_at',
        ]


class VoucherRedemptionSerializer(serializers.Serializer):
    """Serializer for redeeming voucher codes."""

    voucher_code = serializers.CharField(
        max_length=20,
        help_text='The TGD-XXXX-XXXX voucher code.',
    )

    def validate_voucher_code(self, value):
        """Validate that voucher exists and is unused."""
        try:
            voucher = Voucher.objects.get(code=value.upper())
        except Voucher.DoesNotExist:
            raise serializers.ValidationError('Voucher code not found.')

        if voucher.status != Voucher.VoucherStatus.UNUSED:
            raise serializers.ValidationError(f'Voucher has already been {voucher.status}.')

        if voucher.expired_at and voucher.expired_at < serializers.DateTimeField().to_internal_value(
            __import__('django.utils.timezone', fromlist=['now']).now()
        ):
            raise serializers.ValidationError('Voucher has expired.')

        return value


class VoucherBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk actions on vouchers."""

    voucher_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text='List of voucher IDs to perform bulk action on.',
    )
    action = serializers.ChoiceField(
        choices=['void', 'unvoid', 'export'],
        help_text='Bulk action: void, unvoid, or export.',
    )
