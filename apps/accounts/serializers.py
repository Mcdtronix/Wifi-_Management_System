"""
apps/accounts/serializers.py
----------------------------
Serializers for admin users and roles.
"""

from rest_framework import serializers
from django.contrib.auth.models import Permission

from .models import Role, AdminUser


class PermissionSerializer(serializers.ModelSerializer):
    """Read-only serializer for Django Permission objects."""

    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for admin roles with associated permissions."""

    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='permissions',
    )

    class Meta:
        model = Role
        fields = [
            'id',
            'name',
            'level',
            'description',
            'permissions',
            'permission_ids',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class AdminUserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for admin user listings."""

    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = AdminUser
        fields = [
            'id',
            'email',
            'full_name',
            'phone_number',
            'role',
            'role_name',
            'is_active',
            'is_staff',
            'last_login',
            'last_login_ip',
            'created_at',
        ]
        read_only_fields = [
            'last_login',
            'created_at',
        ]


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Full serializer for admin user details with nested role."""

    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        write_only=True,
        required=False,
        source='role',
    )

    class Meta:
        model = AdminUser
        fields = [
            'id',
            'email',
            'full_name',
            'phone_number',
            'role',
            'role_id',
            'is_active',
            'is_staff',
            'last_login',
            'last_login_ip',
            'failed_login_count',
            'locked_until',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'last_login',
            'last_login_ip',
            'failed_login_count',
            'locked_until',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        """Create new admin user with hashed password."""
        password = self.initial_data.get('password')
        user = AdminUser.objects.create_user(**validated_data, password=password)
        return user

    def update(self, instance, validated_data):
        """Update admin user; optionally set new password."""
        password = self.initial_data.get('password')
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new admin users."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = AdminUser
        fields = [
            'email',
            'full_name',
            'phone_number',
            'role',
            'password',
            'password_confirm',
        ]

    def validate(self, data):
        """Ensure passwords match."""
        if data.get('password') != self.initial_data.get('password_confirm'):
            raise serializers.ValidationError(
                {'password_confirm': 'Passwords do not match.'}
            )
        return data

    def create(self, validated_data):
        """Create new admin user with hashed password."""
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        user = AdminUser.objects.create_user(**validated_data, password=password)
        return user
