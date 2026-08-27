"""Order placement and transitions (FR-ORD-01..05) — one transaction each."""
from django.db import transaction
from django.db.models import Max

from carts.models import Cart
from carts.pricing_service import quote
from common.errors import DomainError
from common.models import OutboxMessage, RuntimeConfig
from promotions import services as promo
from promotions.models import Redemption

from .models import IdempotencyRecord, Order, OrderEvent, OrderItem
from .state_machine import can


def record_event(order, to_status, *, actor_type, actor_id=None, reason="", payload=None):
    seq = (order.events.aggregate(m=Max("seq"))["m"] or 0) + 1
    return OrderEvent.objects.create(order=order, seq=seq, from_status=order.status, to_status=to_status,
                                     actor_type=actor_type, actor_id=actor_id, reason=reason, payload=payload or {})


@transaction.atomic
def place(*, user, address, coupon_code="", tip_minor=0, idempotency_key=""):
    """FR-ORD-01: freeze the cart into an order atomically; FR-ORD-02 replay-safe."""
    if idempotency_key:
        record, created = IdempotencyRecord.objects.get_or_create(
            user=user, key=idempotency_key[:64], endpoint="orders.place")
        if not created and record.response is not None:
            return record.response, True  # replay: original outcome, no side effects

    cart = Cart.objects.filter(user=user).first()
    lines = list(cart.items.select_related("item").order_by("id")) if cart else []
    if not lines or not cart.branch:
        raise DomainError("order.empty_cart", "Add items to your cart before checkout.")
    if not address:
        raise DomainError("order.address_required", "A delivery address is required.")
    subtotal = sum(line.line_total_minor for line in lines)
    if subtotal < cart.branch.min_order_minor:
        raise DomainError("order.below_minimum", f"Minimum order for this restaurant is {cart.branch.min_order_minor}.")

    coupon, coupon_model = None, None
    if coupon_code:
        coupon_model = promo.get(coupon_code)
        if not coupon_model:
            raise DomainError("coupon.unknown", "Unknown coupon code.")
        coupon_model = type(coupon_model).objects.select_for_update().get(pk=coupon_model.pk)
        coupon = promo.check(coupon_model, user=user, subtotal_minor=subtotal)

    breakdown = quote(lines=[{"line_total_minor": line.line_total_minor} for line in lines],
                      coupon=coupon, delivery_fee_minor=RuntimeConfig.get("delivery.fee_minor", 5000),
                      tip_minor=tip_minor, vat_bp=RuntimeConfig.get("pricing.vat_bp", 500))
    order = Order.objects.create(
        customer=user, branch=cart.branch, address={
            "label": address.label, "line": address.street, "city": address.city,
            "lat": str(address.lat), "lng": str(address.lng), "instructions": address.directions,
        },
        coupon={"code": coupon_model.code} if coupon_model else {},
        **{k: breakdown[k] for k in ("items_total_minor", "discount_minor", "delivery_fee_minor",
                                     "vat_minor", "tip_minor", "grand_total_minor")},
    )
    OrderItem.objects.bulk_create(OrderItem(
        order=order, menu_item_ref=line.item_id, title_snapshot=line.title_snapshot, qty=line.qty,
        unit_price_minor=line.unit_price_snapshot_minor, options=line.selected_options,
        line_total_minor=line.line_total_minor,
    ) for line in lines)
    record_event(order, "placed", actor_type="customer", actor_id=user.id, payload={"total": breakdown["grand_total_minor"]})
    if coupon_model:
        Redemption.objects.create(coupon=coupon_model, user=user, order_id=order.id)
    deadline = RuntimeConfig.get("orders.accept_timeout_seconds", 600)
    OutboxMessage.emit("order.placed", order=str(order.uuid), branch=str(cart.branch.uuid),
                       total_minor=breakdown["grand_total_minor"], accept_deadline_seconds=deadline)

    response = {"uuid": str(order.uuid), "status": order.status, "grand_total_minor": order.grand_total_minor}
    if idempotency_key:
        record.response = response
        record.status_code = 201
        record.save(update_fields=["response", "status_code"])
    cart.clear()
    return response, False


@transaction.atomic
def transition(order, *, to_status, actor_type, actor_id=None, reason=""):
    """FR-ORD-03/05: guarded transition + audit row + outbox fanout."""
    if not can(order.status, to_status):
        raise DomainError("order.illegal_transition", f"Cannot move an order from {order.status} to {to_status}.", 409)
    from_status = order.status
    order.status = to_status
    if to_status == "accepted":
        from django.utils import timezone
        order.accepted_at = timezone.now()
    if to_status == "delivered":
        from django.utils import timezone
        order.delivered_at = timezone.now()
    order.save()
    event = record_event(order, to_status, actor_type=actor_type, actor_id=actor_id, reason=reason)
    OutboxMessage.emit("order.status_changed", order=str(order.uuid), from_status=from_status,
                       to_status=to_status, actor_type=actor_type, reason=reason)
    return event
