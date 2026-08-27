from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from common.models import TimeStampedModel


class Payment(models.Model):
    """§8.9: one live payment per order; history kept by superseding rows."""

    class Gateway(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        COD = "cod", "Cash on delivery"
        BKASH = "bkash", "bKash"
        NAGAD = "nagad", "Nagad"

    class State(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        REQUIRES_ACTION = "requires_action", "Requires action"
        AUTHORIZED = "authorized", "Authorized"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"
        VOIDED = "voided", "Voided"

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="payment")
    gateway = models.CharField(max_length=10, choices=Gateway.choices)
    gateway_reference = models.CharField(max_length=255, blank=True)
    amount_minor = models.BigIntegerField(validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="BDT")
    state = models.CharField(max_length=16, choices=State.choices, default=State.INITIATED)
    brand_last4 = models.CharField(max_length=4, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["order"], condition=Q(state__in=["initiated", "requires_action", "authorized"]),
            name="one_live_payment_per_order")]


class Refund(models.Model):
    class State(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    class Reason(models.TextChoices):
        MISTAKE = "mistake", "Mistake"
        ITEM_ISSUE = "item_issue", "Item issue"
        LATE = "late", "Late"
        NO_SHOW = "no_show", "No show"
        GOODWILL = "goodwill", "Goodwill"

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    amount_minor = models.BigIntegerField(validators=[MinValueValidator(1)])
    reason = models.CharField(max_length=12, choices=Reason.choices)
    state = models.CharField(max_length=10, choices=State.choices, default=State.REQUESTED)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="refunds_requested")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="refunds_approved")
    processed_at = models.DateTimeField(null=True, blank=True)


class LedgerEntry(models.Model):
    """Signed double-entry rows; pairs share a batch_uuid (§8.9)."""

    class EntryType(models.TextChoices):
        ORDER_CAPTURE = "order_capture", "Order capture"
        PLATFORM_COMMISSION = "platform_commission", "Platform commission"
        VENDOR_SETTLEMENT = "vendor_settlement", "Vendor settlement"
        COURIER_PAYOUT = "courier_payout", "Courier payout"
        REFUND_OUT = "refund_out", "Refund out"
        ADJUSTMENT = "adjustment", "Adjustment"

    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="ledger_entries")
    payee_type = models.CharField(max_length=10)  # platform | vendor | courier
    payee_id = models.BigIntegerField(null=True, blank=True)
    amount_minor = models.BigIntegerField()  # signed
    currency = models.CharField(max_length=3, default="BDT")
    batch_uuid = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Invoice(models.Model):
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="invoice")
    series = models.CharField(max_length=6)
    number = models.PositiveIntegerField()
    full_number = models.CharField(max_length=20, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.number:
            last = Invoice.objects.filter(series=self.series).aggregate(m=models.Max("number"))["m"] or 0
            self.number = last + 1
            self.full_number = f"BD-{self.series}-{self.number:06d}"
        super().save(*args, **kwargs)


class WebhookEvent(models.Model):
    class State(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        IGNORED = "ignored", "Ignored"
        DEAD = "dead", "Dead"

    provider = models.CharField(max_length=10)
    event_id = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    state = models.CharField(max_length=10, choices=State.choices, default=State.RECEIVED)
    retries = models.PositiveSmallIntegerField(default=0)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["provider", "event_id"], name="unique_psp_event")]
