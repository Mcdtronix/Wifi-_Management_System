"""
apps/notifications/models.py
-----------------------------
WhatsApp and multi-channel notification system.
Manages notification templates, delivery tracking, and communication preferences.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from utils.mixins import BaseModel


class NotificationTemplate(BaseModel):
    """
    Reusable message template for various notification types.
    Supports variable substitution (e.g. {subscriber_name}, {expiry_date}).
    """

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", _("WhatsApp")
        SMS = "sms", _("SMS")
        EMAIL = "email", _("Email")
        IN_APP = "in_app", _("In-App")

    class EventType(models.TextChoices):
        WELCOME = "welcome", _("Welcome Message")
        SUBSCRIPTION_ACTIVATED = "subscription_activated", _("Subscription Activated")
        SUBSCRIPTION_RENEWED = "subscription_renewed", _("Subscription Renewed")
        EXPIRY_WARNING_7D = "expiry_warning_7d", _("Expiry Warning (7 days)")
        EXPIRY_WARNING_3D = "expiry_warning_3d", _("Expiry Warning (3 days)")
        EXPIRY_WARNING_1D = "expiry_warning_1d", _("Expiry Warning (1 day)")
        SUBSCRIPTION_EXPIRED = "subscription_expired", _("Subscription Expired")
        QUOTA_WARNING = "quota_warning", _("Quota Warning (80%)")
        QUOTA_EXCEEDED = "quota_exceeded", _("Quota Exceeded")
        DEVICE_CHANGE_APPROVED = "device_change_approved", _("Device Change Approved")
        DEVICE_CHANGE_REJECTED = "device_change_rejected", _("Device Change Rejected")
        PAYMENT_CONFIRMATION = "payment_confirmation", _("Payment Confirmation")
        SECURITY_ALERT = "security_alert", _("Security Alert")

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Template Name"),
    )
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        db_index=True,
        verbose_name=_("Event Type"),
    )
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.WHATSAPP,
        verbose_name=_("Primary Channel"),
    )
    subject = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Subject"),
        help_text=_("For email notifications."),
    )
    body = models.TextField(
        verbose_name=_("Message Body"),
        help_text=_("Use {variable} syntax for substitution."),
    )
    variables = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Variables"),
        help_text=_("Available variables for this template."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        db_table = "notifications_template"
        ordering = ["event_type"]
        verbose_name = _("Notification Template")
        verbose_name_plural = _("Notification Templates")
        unique_together = [["event_type", "channel"]]

    def __str__(self):
        return f"{self.name} ({self.get_channel_display()})"


class Notification(BaseModel):
    """
    Sent notification record with delivery tracking.
    One record per message to one recipient.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued")
        SENT = "sent", _("Sent")
        DELIVERED = "delivered", _("Delivered")
        FAILED = "failed", _("Failed")
        BOUNCED = "bounced", _("Bounced")
        UNSUBSCRIBED = "unsubscribed", _("Unsubscribed")

    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )
    template = models.ForeignKey(
        NotificationTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
        verbose_name=_("Template"),
    )
    channel = models.CharField(
        max_length=20,
        choices=NotificationTemplate.Channel.choices,
        verbose_name=_("Channel"),
    )
    recipient = models.CharField(
        max_length=100,
        verbose_name=_("Recipient"),
        help_text=_("Phone (WhatsApp/SMS) or email address."),
    )
    subject = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Subject"),
    )
    body = models.TextField(verbose_name=_("Message Body"))
    
    # Delivery tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
        verbose_name=_("Status"),
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Sent At"),
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Delivered At"),
    )
    external_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("External ID"),
        help_text=_("Message ID from WhatsApp/SMS provider."),
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("Error Message"),
    )
    retry_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Retry Count"),
    )
    
    # Context
    event_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Event Type"),
    )
    context_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Context Data"),
    )

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        indexes = [
            models.Index(fields=["subscriber", "-created_at"], name="idx_notif_sub_date"),
            models.Index(fields=["status"], name="idx_notif_status"),
            models.Index(fields=["channel"], name="idx_notif_channel"),
        ]

    def __str__(self):
        return f"{self.get_channel_display()} → {self.subscriber.username} ({self.get_status_display()})"


class NotificationPreference(BaseModel):
    """
    Per-subscriber notification preferences.
    Allows subscribers to opt-out of specific notification types or channels.
    """

    subscriber = models.OneToOneField(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="notification_preference",
        verbose_name=_("Subscriber"),
    )
    receive_whatsapp = models.BooleanField(
        default=True,
        verbose_name=_("Receive WhatsApp"),
    )
    receive_sms = models.BooleanField(
        default=True,
        verbose_name=_("Receive SMS"),
    )
    receive_email = models.BooleanField(
        default=True,
        verbose_name=_("Receive Email"),
    )
    receive_expiry_warnings = models.BooleanField(
        default=True,
        verbose_name=_("Subscription Expiry Warnings"),
    )
    receive_quota_warnings = models.BooleanField(
        default=True,
        verbose_name=_("Quota Warnings"),
    )
    receive_security_alerts = models.BooleanField(
        default=True,
        verbose_name=_("Security Alerts"),
    )
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Quiet Hours Start"),
        help_text=_("Do not send notifications between these hours."),
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Quiet Hours End"),
    )

    class Meta:
        db_table = "notifications_preference"
        verbose_name = _("Notification Preference")
        verbose_name_plural = _("Notification Preferences")

    def __str__(self):
        return f"Preferences for {self.subscriber.username}"
