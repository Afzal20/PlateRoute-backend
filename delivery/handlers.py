from common.events import on
from orders.models import Order

from . import services


@on("order.status_changed")
def dispatch_on_ready(payload):
    """FR-DLV-01: a DeliveryTask is armed the moment an order is ready."""
    if payload.get("to_status") != "ready":
        return
    if order := Order.objects.filter(uuid=payload.get("order")).select_related("branch").first():
        services.create_task_for_order(order)
