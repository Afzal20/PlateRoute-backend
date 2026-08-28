from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class NotificationTemplate(models.Model):
    code = models.CharField(max_length=60, unique=True)  # e.g. order_placed_vendor
    channel = models.CharField(max_length=5, choices=[("email", "Email"), ("push", "Push"), ("sms", "SMS")])
    locale = models.CharField(max_length=8, default="en")
    subject = models.CharField(max_length=150, blank=True)
    body = models.TextField()
    active = models.BooleanField(default=True)


class DeviceRegistry(TimeStampedModel):
    """FCM tokens per user (FR-NOT-02)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    fcm_token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=8, choices=[("android", "Android"), ("ios", "iOS")])
    app_version = models.CharField(max_length=24, blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)


class NotificationOutbox(TimeStampedModel):
    """Every send funnels through here (at-least-once, dedup via dedup_key)."""

    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    dedup_key = models.CharField(max_length=120, null=True, blank=True, unique=True)
    channel = models.CharField(max_length=5, choices=NotificationTemplate.channel.field.choices)
    recipient_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    recipient = models.CharField(max_length=255, blank=True)  # address blob for guests
    template = models.ForeignKey(NotificationTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    context = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=8, choices=State.choices, default=State.QUEUED, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)


class NotificationPreference(models.Model):
    class Kind(models.TextChoices):
        MARKETING = "marketing", "Marketing"
        ORDER_UPDATES = "order_updates", "Order updates"
        COURIER_ALERTS = "courier_alerts", "Courier alerts"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_prefs")
    kind = models.CharField(max_length=15, choices=Kind.choices)
    email = models.BooleanField(default=True)
    push = models.BooleanField(default=True)
    sms = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "kind"], name="unique_pref_kind")]