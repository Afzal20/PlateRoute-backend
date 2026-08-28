from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError
from common.permissions import role_required
from orders.models import Order

from . import services
from .models import CourierProfile, DeliveryOffer, DeliveryTask, LocationPing


class ProfileView(APIView):
    """FR-DLV-03 / MOB-CUR-01: courier vehicle record + shift toggle."""

    def get(self, request):
        profile, _ = CourierProfile.objects.get_or_create(user=request.user)
        return Response({"vehicle": profile.vehicle, "plate": profile.plate, "license": profile.license,
                         "is_online": profile.is_online, "last_online_at": profile.last_online_at})

    def put(self, request):
        profile, _ = CourierProfile.objects.get_or_create(user=request.user)
        for field in ("vehicle", "plate", "license"):
            if field in request.data:
                setattr(profile, field, request.data[field])
        if "online" in request.data:
            profile.is_online = bool(request.data["online"])
            profile.last_online_at = timezone.now() if profile.is_online else profile.last_online_at
        profile.save()
        return Response({"is_online": profile.is_online, "vehicle": profile.vehicle})


class OfferListView(APIView):
    """The courier's live, unexpired task offers."""

    def get(self, request):
        profile, _ = CourierProfile.objects.get_or_create(user=request.user)
        offers = (DeliveryOffer.objects.filter(courier=profile, state=DeliveryOffer.State.SENT, expires_at__gt=timezone.now())
                  .select_related("task", "task__order"))
        return Response([
            {"id": o.id, "task": str(o.task.uuid), "fee_minor": o.task.courier_fee_minor,
             "pickup": [float(o.task.pickup_lat), float(o.task.pickup_lng)],
             "dropoff": [float(o.task.dropoff_lat), float(o.task.dropoff_lng)],
             "promised_eta_minutes": o.task.promised_eta_minutes, "expires_at": o.expires_at}
            for o in offers
        ])


class OfferActionView(APIView):
    """POST /delivery/offers/{id}/claim|decline/ — accept-once semantics."""

    def post(self, request, pk, action):
        profile, _ = CourierProfile.objects.get_or_create(user=request.user)
        offer = get_object_or_404(DeliveryOffer, pk=pk)
        if action == "claim":
            task = services.claim(offer, courier_profile=profile)
            return Response({"task": str(task.uuid), "state": task.state})
        if offer.courier_id != profile.id:
            raise DomainError("delivery.not_yours", "Not your offer.", status.HTTP_403_FORBIDDEN)
        offer.state = DeliveryOffer.State.DECLINED
        offer.save(update_fields=["state"])
        return Response({"state": offer.state})


class TripView(APIView):
    """POST /delivery/tasks/{uuid}/trip/ {action: at_vendor|picked|arrived|dropped}."""

    def post(self, request, uuid):
        profile = get_object_or_404(CourierProfile, user=request.user)
        task = get_object_or_404(DeliveryTask, uuid=uuid)
        task = services.trip_action(task, action=request.data.get("action", ""), courier_profile=profile)
        return Response({"task": str(task.uuid), "state": task.state,
                         "order_status": task.order.status})


class PingView(APIView):
    """FR-DLV-04: batched telemetry ingest; optional task uuid per ping."""

    def post(self, request):
        profile = get_object_or_404(CourierProfile, user=request.user)
        pings = request.data.get("pings", [])
        rows = []
        for p in pings:
            task = DeliveryTask.objects.filter(uuid=p.get("task")).first() if p.get("task") else None
            rows.append(LocationPing(courier=profile, task=task, lat=p["lat"], lng=p["lng"],
                                     speed_mps=p.get("speed"), heading_deg=p.get("heading")))
        LocationPing.objects.bulk_create(rows)
        return Response({"count": len(rows)})


class TrackingView(APIView):
    """Customer/merchant/courier view of a live order (FR-NOT-03 counterpart)."""

    def get(self, request, order_uuid):
        order = get_object_or_404(Order.objects.select_related("delivery_task"), uuid=order_uuid)
        user = request.user
        task = getattr(order, "delivery_task", None)
        is_vendor = order.branch.is_managed_by(user)
        is_courier = task and task.courier and task.courier.user_id == user.id
        if order.customer_id != user.id and not is_vendor and not is_courier and not (user.is_staff or user.role == "operator"):
            raise DomainError("delivery.forbidden", "Not a participant of this order.", status.HTTP_403_FORBIDDEN)
        last = task.courier.pings.order_by("-recorded_at").first() if task and task.courier else None
        return Response({
            "order": str(order.uuid), "order_status": order.status,
            "task_state": task.state if task else None,
            "courier_location": [float(last.lat), float(last.lng)] if last else None,
            "last_ping_at": last.recorded_at if last else None,
            "promised_eta_minutes": task.promised_eta_minutes if task else None,
        })
