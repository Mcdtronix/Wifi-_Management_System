"""
utils/mixins.py
---------------
Abstract model mixins shared across all apps.
"""

import uuid
from django.db import models


class UUIDPrimaryKeyMixin(models.Model):
    """Replace integer PK with UUID — prevents enumeration attacks."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )

    class Meta:
        abstract = True


class TimestampMixin(models.Model):
    """Auto-managed created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """
    Marks records as deleted without physically removing them.
    Preserves referential integrity and audit trails.
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])


class BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Full-featured base model: UUID PK + timestamps + soft-delete.
    Inherit from this in all domain models.
    """

    class Meta:
        abstract = True