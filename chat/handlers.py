from common.events import on
from orders.models import Order

from .models import Participant, Thread
from .services import _order_members


@on("order.status_changed")
def welcome_courier_to_thread(payload):
    """Courier joins the order thread as soon as the task is claimed (picked)."""
    if payload.get("to_status") != "picked":
        return
    order = Order.objects.filter(uuid=payload.get("order")).first()
    if not order:
        return
    thread = Thread.objects.filter(kind="order", order=order).first()
    if not thread:
        return
    for member in _order_members(order):
        Participant.objects.get_or_create(thread=thread, user=member["user"], defaults={"role": member["role"]})