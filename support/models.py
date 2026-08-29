from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Ticket(TimeStampedModel):
    """FR-RVW-04 / FR-AUTH-12: user/operator support conversations."""

    class Category(models.TextChoices):
        ORDER_ISSUE = "order_issue", "Order issue"
        REFUND_REQUEST = "refund_request", "Refund request"
        ACCOUNT = "account", "Account"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        WAITING_CUSTOMER = "waiting_customer", "Waiting on customer"
        RESOLVED = "resolved", "Resolved"
        REOPENED = "reopened", "Reopened"

    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets")
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets_opened")
    category = models.CharField(max_length=15, choices=Category.choices, default=Category.OTHER)
    priority = models.CharField(max_length=6, choices=[("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")], default="normal")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    subject = models.CharField(max_length=150)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    sla_due_at = models.DateTimeField(null=True, blank=True, db_index=True)


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    body = models.TextField(max_length=4000)
    internal_note = models.BooleanField(default=False)  # operators-only visibility
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)