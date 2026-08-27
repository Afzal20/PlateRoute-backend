from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from common.models import TimeStampedModel


class Order(TimeStampedModel):
    """§8.7: frozen-price order with an append-only audit trail."""

    class Status(models.TextChoices):
        PLACED = "placed", "Placed"
        ACCEPTED = "accepted", "Accepted"
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready for pickup"
        PICKED = "picked", "Picked up"
        OUT = "out", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        REJECTED = "rejected", "Rejected"
        CANCELLED_CUSTOMER = "cancelled_customer", "Cancelled by customer"
        CANCELLED_RESTAURANT = "cancelled_restaurant", "Cancelled by restaurant"
        CANCELLED_PLATFORM = "cancelled_platform", "Cancelled by platform"
        FAILED_PAYMENT = "failed_payment", "Failed payment"
        REFUND_PENDING = "refund_pending", "Refund pending"
        REFUNDED = "refunded", "Refunded"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    branch = models.ForeignKey("vendors.Branch", on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED, db_index=True)
    currency = models.CharField(max_length=3, default="BDT")
    items_total_minor = models.BigIntegerField(default=0)
    discount_minor = models.BigIntegerField(default=0, validators=[MinValueValidator(0)])
    delivery_fee_minor = models.BigIntegerField(default=0)
    vat_minor = models.BigIntegerField(default=0)
    tip_minor = models.BigIntegerField(default=0)
    grand_total_minor = models.BigIntegerField(default=0)
    address = models.JSONField(default=dict)   # {line, city, lat, lng, instructions}
    coupon = models.JSONField(default=dict, blank=True)
    eta = models.JSONField(default=dict, blank=True)
    placed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        indexes = [models.Index(fields=["customer", "status", "-placed_at"])]

    def __str__(self):
        return f"#{self.pk} {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item_ref = models.BigIntegerField()
    title_snapshot = models.CharField(max_length=150)
    qty = models.PositiveSmallIntegerField()
    unit_price_minor = models.BigIntegerField()
    options = models.JSONField(default=list, blank=True)
    line_total_minor = models.BigIntegerField()


class OrderEvent(models.Model):
    """Append-only audit row; one per transition (FR-ORD-05)."""

    class ActorType(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        VENDOR = "vendor", "Vendor"
        COURIER = "courier", "Courier"
        SYSTEM = "system", "System"
        OPERATOR = "operator", "Operator"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    seq = models.PositiveBigIntegerField()
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    actor_type = models.CharField(max_length=10, choices=ActorType.choices)
    actor_id = models.BigIntegerField(null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["order", "seq"], name="unique_order_seq")]
        ordering = ("seq",)


class IdempotencyRecord(TimeStampedModel):
    """FR-ORD-02: replays of mutating calls return the original outcome."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="idempotency_keys")
    key = models.CharField(max_length=64)
    endpoint = models.CharField(max_length=100)
    response = models.JSONField(null=True, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "key"], condition=~models.Q(key=""), name="unique_idempotency_key")]
