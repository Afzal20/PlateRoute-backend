"""Dispatch engine: nearest-first offers, expiry cascade, atomic claims."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from common.errors import DomainError
from common.geo import haversine_m
from common.models import OutboxMessage, RuntimeConfig

from .models import CourierProfile, DeliveryOffer, DeliveryTask


def _point(profile):
    ping = profile.pings.order_by("-recorded_at").first()
    return (float(ping.lat), float(ping.lng)) if ping else None


def create_task_for_order(order):
    """FR-DLV-01: capture geo + SLA + fee when the order turns ready."""
    if hasattr(order, "delivery_task"):
        return order.delivery_task
    drop_lat = Decimal(order.address.get("lat") or "0")
    drop_lng = Decimal(order.address.get("lng") or "0")
    task = DeliveryTask.objects.create(
        order=order, pickup_lat=order.branch.lat, pickup_lng=order.branch.lng,
        dropoff_lat=drop_lat, dropoff_lng=drop_lng,
        promised_eta_minutes=order.branch.prep_minutes + 20,
        courier_fee_minor=RuntimeConfig.get("delivery.courier_fee_minor", 4000),
    )
    offer_task(task)
    return task


def offer_task(task, *, exclude=()):
    """FR-DLV-02: offer to the K nearest online couriers, TTL-expiring.
    Couriers already holding an expired offer get their row re-armed."""
    online = list(CourierProfile.objects.filter(is_online=True).exclude(id__in=[c.id for c in exclude]))
    if not online:
        return []
    pickup = (float(task.pickup_lat), float(task.pickup_lng))
    ranked = sorted(online, key=lambda c: (haversine_m(pickup, _point(c)) if _point(c) else float("inf"), c.id))[:6]
    expires = timezone.now() + timezone.timedelta(seconds=RuntimeConfig.get("delivery.offer_ttl_seconds", 60))
    existing = {o.courier_id: o for o in task.offers.all()}
    for courier in ranked:
        offer = existing.get(courier.id)
        if offer:
            offer.state = DeliveryOffer.State.SENT
            offer.expires_at = expires
            offer.save(update_fields=["state", "expires_at"])
        else:
            DeliveryOffer.objects.create(task=task, courier=courier, expires_at=expires)
    task.state = DeliveryTask.State.OFFERING
    task.save(update_fields=["state"])
    OutboxMessage.emit("delivery.offered", task=str(task.uuid),
                       couriers=[c.user_id for c in ranked], fee_minor=task.courier_fee_minor)
    return ranked


def sweep_expired():
    """Offer TTL cascade: re-offer excluding decliners, or give up."""
    now = timezone.now()
    expired = DeliveryOffer.objects.filter(state=DeliveryOffer.State.SENT, expires_at__lte=now)
    expired.update(state=DeliveryOffer.State.EXPIRED)
    touched = DeliveryTask.objects.filter(offers__state=DeliveryOffer.State.EXPIRED, state=DeliveryTask.State.OFFERING).distinct()
    for task in touched:
        decliners = list(CourierProfile.objects.filter(offers__task=task, offers__state=DeliveryOffer.State.DECLINED))
        if not offer_task(task, exclude=decliners):
            task.state = DeliveryTask.State.EXPIRED_NO_COURIER
            task.save(update_fields=["state"])
    return touched.count()


@transaction.atomic
def claim(offer, *, courier_profile):
    """FR-DLV-03: single-winner atomic claim on an offering task."""
    if offer.courier_id != courier_profile.id or offer.state != DeliveryOffer.State.SENT:
        raise DomainError("delivery.offer_unavailable", "This offer is not yours or no longer valid.", 409)
    updated = DeliveryTask.objects.filter(uuid=offer.task.uuid, state=DeliveryTask.State.OFFERING).update(
        state=DeliveryTask.State.CLAIMED, courier=courier_profile, claimed_at=timezone.now())
    if not updated:
        raise DomainError("delivery.already_claimed", "Another courier already claimed this task.", 409)
    offer.state = DeliveryOffer.State.ACCEPTED
    offer.save(update_fields=["state"])
    offer.task.offers.exclude(pk=offer.pk).update(state=DeliveryOffer.State.EXPIRED)
    return DeliveryTask.objects.get(pk=offer.task_id)


@transaction.atomic
def trip_action(task, *, action, courier_profile):
    """FR-DLV-03: trip states mapped onto order transitions (§4 rule 5)."""
    from orders.services import transition
    if task.courier_id != courier_profile.id:
        raise DomainError("delivery.not_yours", "Not your task.", 403)
    order = task.order
    if action == "at_vendor":
        task.state = DeliveryTask.State.AT_VENDOR
    elif action == "picked":
        task.state, task.picked_at = DeliveryTask.State.PICKED, timezone.now()
        transition(order, to_status="picked", actor_type="courier", actor_id=courier_profile.user_id)
        transition(order, to_status="out", actor_type="courier", actor_id=courier_profile.user_id)
    elif action == "arrived":
        task.state = DeliveryTask.State.ARRIVED
    elif action == "dropped":
        task.state, task.dropped_at = DeliveryTask.State.DROPPED, timezone.now()
        transition(order, to_status="delivered", actor_type="courier", actor_id=courier_profile.user_id)
    else:
        raise DomainError("delivery.bad_action", "Unknown trip action.")
    task.save()
    return task
