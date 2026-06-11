"""
apps/audit/models.py
--------------------
Comprehensive audit logging for compliance and security investigations.
Tracks all user and admin actions with full context.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from utils.mixins import BaseModel


class AuditLog(BaseModel):
    """
    Immutable audit record of system event.
    Tracks WHO did WHAT on WHICH object at WHEN with full change context.
    """

    class Action(models.TextChoices):
        CREATE = "create", _("Created")
        UPDATE = "update", _("Updated")
        DELETE = "delete", _("Deleted")
        LOGIN = "login", _("Login")
        LOGOUT = "logout", _("Logout")
        AUTHENTICATE = "authenticate", _("Authentication Attempt")
        AUTHORIZE = "authorize", _("Authorization Check")
        SUSPEND = "suspend", _("Account Suspended")
        ACTIVATE = "activate", _("Account Activated")
        RESET_PASSWORD = "reset_password", _("Password Reset")
        EXPORT = "export", _("Data Exported")
        IMPORT = "import", _("Data Imported")
        APPROVE = "approve", _("Approved")
        REJECT = "reject", _("Rejected")
        REDEEM = "redeem", _("Voucher Redeemed")
        ASSIGN_PLAN = "assign_plan", _("Assign Plan")
        RENEW_SUBSCRIPTION = "renew_subscription", _("Renew Subscription")
        REGISTER_DEVICE = "register_device", _("Register Device")
        REVOKE_DEVICE = "revoke_device", _("Revoke Device")
        APPROVE_DEVICE_CHANGE = "approve_device_change", _("Approve Device Change")
        CREATE_SUBSCRIBER = "create_subscriber", _("Create Subscriber")
        SUSPEND_SUBSCRIBER = "suspend_subscriber", _("Suspend Subscriber")
        ACTIVATE_SUBSCRIBER = "activate_subscriber", _("Activate Subscriber")
        GENERATE_VOUCHERS = "generate_vouchers", _("Generate Vouchers")
        ADMIN_CREATE_USER = "admin_create_user", _("Admin Create User")

    class Severity(models.IntegerChoices):
        DEBUG = 0, _("Debug")
        INFO = 1, _("Info")
        WARNING = 2, _("Warning")
        ERROR = 3, _("Error")
        CRITICAL = 4, _("Critical")

    # WHO performed the action
    actor_user = models.ForeignKey(
        "accounts.AdminUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs_as_actor",
        verbose_name=_("Actor (Admin)"),
        help_text=_("Null if action by system or external service."),
    )
    actor_subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs_as_actor",
        verbose_name=_("Actor (Subscriber)"),
        help_text=_("If action by subscriber via captive portal."),
    )
    actor_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Actor IP Address"),
    )

    # WHAT action
    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        db_index=True,
        verbose_name=_("Action"),
    )

    # WHICH object (generic FK to any model)
    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Object Type"),
    )
    object_id = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("Object ID"),
    )
    affected_object = GenericForeignKey("content_type", "object_id")

    # WHAT changed
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Human-readable summary of what happened."),
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Field Changes"),
        help_text=_("Dict of {field: {old, new}} for updates."),
    )
    
    # Context
    severity = models.PositiveSmallIntegerField(
        choices=Severity.choices,
        default=Severity.INFO,
        db_index=True,
        verbose_name=_("Severity"),
    )
    source = models.CharField(
        max_length=50,
        default="api",
        verbose_name=_("Source"),
        help_text=_("E.g. 'api', 'admin_panel', 'celery_task', 'freeradius'."),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Additional Metadata"),
    )

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        indexes = [
            models.Index(fields=["action", "-created_at"], name="idx_audit_action_date"),
            models.Index(fields=["actor_subscriber", "-created_at"], name="idx_audit_subscriber_date"),
            models.Index(fields=["actor_user", "-created_at"], name="idx_audit_admin_date"),
            models.Index(fields=["severity"], name="idx_audit_severity"),
        ]

    def __str__(self):
        actor = self.actor_user or self.actor_subscriber or "System"
        return f"[{self.action}] {actor} — {self.created_at.isoformat()}"

    @classmethod
    def log(cls, action, obj, description, actor_user=None, actor_subscriber=None, request=None, severity=Severity.INFO, changes=None, metadata=None):
        """Helper to create an audit log entry."""
        ip = None
        if request:
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            else:
                ip = request.META.get("REMOTE_ADDR", "")

        action_val = getattr(action, 'value', action)
        content_type = ContentType.objects.get_for_model(obj) if obj else None
        object_id = str(obj.pk) if obj else ""

        return cls.objects.create(
            action=action_val,
            actor_user=actor_user,
            actor_subscriber=actor_subscriber,
            actor_ip=ip,
            content_type=content_type,
            object_id=object_id,
            description=description,
            changes=changes or {},
            severity=severity,
            metadata=metadata or {}
        )


class AdminActivityLog(BaseModel):
    """
    Focused audit trail for administrative actions only.
    Tracks sensitive operations: user creation, voucher generation, subscription changes.
    """

    class AdminAction(models.TextChoices):
        CREATE_USER = "create_user", _("Create User")
        DELETE_USER = "delete_user", _("Delete User")
        EDIT_USER = "edit_user", _("Edit User")
        RESET_PASSWORD = "reset_password", _("Reset Password")
        CHANGE_ROLE = "change_role", _("Change Role")
        SUSPEND_SUBSCRIBER = "suspend_subscriber", _("Suspend Subscriber")
        ACTIVATE_SUBSCRIBER = "activate_subscriber", _("Activate Subscriber")
        RENEW_SUBSCRIPTION = "renew_subscription", _("Renew Subscription")
        GENERATE_VOUCHER = "generate_voucher", _("Generate Voucher")
        APPROVE_DEVICE_CHANGE = "approve_device_change", _("Approve Device Change")
        REJECT_DEVICE_CHANGE = "reject_device_change", _("Reject Device Change")
        MODIFY_BANDWIDTH = "modify_bandwidth", _("Modify Bandwidth")
        EXPORT_DATA = "export_data", _("Export Data")
        BULK_OPERATION = "bulk_operation", _("Bulk Operation")

    admin = models.ForeignKey(
        "accounts.AdminUser",
        on_delete=models.CASCADE,
        related_name="activity_logs",
        verbose_name=_("Administrator"),
    )
    action = models.CharField(
        max_length=50,
        choices=AdminAction.choices,
        db_index=True,
        verbose_name=_("Action"),
    )
    target_user = models.ForeignKey(
        "subscribers.Subscriber",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Target Subscriber"),
    )
    description = models.TextField(verbose_name=_("Action Description"))
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("IP Address"),
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_("User Agent"),
    )
    affected_records_count = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Records Affected"),
        help_text=_("For bulk operations."),
    )

    class Meta:
        db_table = "audit_admin_activity"
        ordering = ["-created_at"]
        verbose_name = _("Admin Activity")
        verbose_name_plural = _("Admin Activities")
        indexes = [
            models.Index(fields=["admin", "-created_at"], name="idx_admin_activity_date"),
            models.Index(fields=["action"], name="idx_admin_activity_action"),
        ]

    def __str__(self):
        return f"{self.admin.full_name} — {self.get_action_display()} ({self.created_at})"
