from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Thread(TimeStampedModel):
    """Order/support context anchored conversation; §10."""

    uuid_hint = None  # inherited from TimeStampedModel

    kind = models.CharField(max_length=15, choices=[("order", "Order"), ("support", "Support")], default="order")
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.CASCADE, related_name="threads")
    subject = models.CharField(max_length=150, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_created")
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    message_count = models.PositiveIntegerField(default=0)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_reason = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.kind}#{self.order_id or ''}"


class Participant(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        VENDOR = "vendor_staff", "Vendor staff"
        COURIER = "courier", "Courier"
        OPERATOR = "operator", "Operator"

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_participants")
    role = models.CharField(max_length=12, choices=Role.choices)
    last_read_message_id = models.BigIntegerField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    muted_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["thread", "user"], name="unique_thread_participant")]


class Message(models.Model):
    class Kind(models.TextChoices):
        TEXT = "text", "Text"
        SYSTEM = "system", "System"
        EVENT = "event", "Event"

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.TEXT)
    body = models.TextField(max_length=4000)
    reply_to = models.IntegerField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)
        indexes = [models.Index(fields=["thread", "-id"])]


class Report(models.Model):
    class Outcome(models.TextChoices):
        REMOVED = "removed", "Removed"
        DISMISSED = "dismissed", "Dismissed"
        NO_ACTION = "no_action", "No action"

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reports")
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made")
    reason = models.CharField(max_length=200)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    outcome = models.CharField(max_length=10, choices=Outcome.choices, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)