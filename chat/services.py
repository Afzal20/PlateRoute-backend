"""Direct messaging service — single home of thread scopes & permissions (§10)."""
from django.db import models
from django.utils import timezone

from common.errors import DomainError
from rest_framework import status

from .models import Message, Participant, Thread


def participants_of(user):
    """Threads the user may see, plus unread counts derived from watermarks."""
    return Participant.objects.filter(user=user, left_at__isnull=True).values_list("thread_id", flat=True)


def get_or_create_order_thread(order, user):
    """Idempotent bootstrap: customer+merchant (courier joins once claimed)."""
    thread = Thread.objects.filter(kind="order", order=order).first()
    if not thread:
        thread = Thread.objects.create(kind="order", order=order, subject=f"Order #{order.pk}", created_by=user)
        for member in _order_members(order):
            Participant.objects.get_or_create(thread=thread, user=member["user"], defaults={"role": member["role"]})
    return thread


def _order_members(order):
    yield {"user": order.customer, "role": Participant.Role.CUSTOMER}
    branch = order.branch
    owner = branch.vendor.owner
    yield {"user": owner, "role": Participant.Role.VENDOR}
    for staff in branch.staff.all():
        yield {"user": staff.user, "role": Participant.Role.VENDOR}
    task = getattr(order, "delivery_task", None)
    if task and task.courier:
        yield {"user": task.courier.user, "role": Participant.Role.COURIER}


def can_send(user, thread):
    """Message window (§10): participant + thread not closed + text cap."""
    if not Participant.objects.filter(thread=thread, user=user, left_at__isnull=True).exists():
        raise DomainError("chat.not_participant", "You are not a member of this thread.", status.HTTP_403_FORBIDDEN)
    if thread.closed_at:
        raise DomainError("chat.thread_closed", "This conversation is closed.", status.HTTP_403_FORBIDDEN)


def send(user, thread, body, kind=Message.Kind.TEXT):
    """Write a message (WS mirrors this; never writes domain state alone)."""
    body = (body or "").strip()
    if not body:
        raise DomainError("chat.empty", "Message cannot be empty.")
    if len(body) > 4000:
        raise DomainError("chat.too_long", "Messages are capped at 4000 characters.")
    message = Message.objects.create(thread=thread, sender=user, body=body, kind=kind)
    Thread.objects.filter(pk=thread.pk).update(last_message_at=timezone.now(), message_count=models.F("message_count") + 1)
    return message


def advance_watermark(user, thread, *, message_id):
    """§10 unread model: monotonic watermark per participant."""
    participant = Participant.objects.get(thread=thread, user=user)
    if message_id >= (participant.last_read_message_id or 0):
        participant.last_read_message_id = message_id
        participant.save(update_fields=["last_read_message_id"])
    return participant


def unread_count(thread, user):
    participant = Participant.objects.get(thread=thread, user=user)
    return Message.objects.filter(thread=thread, id__gt=participant.last_read_message_id or 0).exclude(sender=user).count()