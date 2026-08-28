from common.events import on
from orders.models import Order

from . import services


@on("order.placed")
def notify_vendor_placed(payload):
    """FR-NOT-01: alert the merchant the moment an order is placed."""
    order = Order.objects.filter(uuid=payload.get("order")).select_related("branch", "branch__vendor").first()
    if order:
        services.enqueue(code="order_placed_vendor", user=order.branch.vendor.owner,
                         context={"order_pk": order.pk, "total": payload.get("total_minor")},
                         dedup_key=f"order-placed-{order.pk}")