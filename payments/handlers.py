from common.events import on
from orders.models import Order

from . import services
from .models import Payment


@on("order.status_changed")
def cod_settle_on_delivery(payload):
    """COD payments are captured the moment an order is delivered (§8.9)."""
    if payload.get("to_status") != "delivered":
        return
    if order := Order.objects.filter(uuid=payload.get("order")).first():
        services.settle_cod_on_delivery(order)


@on("order.status_changed")
def void_unpaid_on_cancellation(payload):
    """Unpaid card sessions die with the order so a new one can start."""
    if payload.get("to_status") not in ("rejected", "cancelled_customer", "cancelled_restaurant", "cancelled_platform"):
        return
    Payment.objects.filter(order__uuid=payload.get("order"),
                           state__in=[Payment.State.INITIATED, Payment.State.REQUIRES_ACTION, Payment.State.AUTHORIZED],
                           ).exclude(gateway=Payment.Gateway.COD).update(state=Payment.State.VOIDED)
