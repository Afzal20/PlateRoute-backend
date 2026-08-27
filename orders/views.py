from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from addresses.models import Address
from common.errors import DomainError

from . import services
from .models import Order
from .serializers import OrderSerializer

VENDOR_TARGETS = {"accepted", "rejected", "preparing", "ready", "cancelled_restaurant"}
CUSTOMER_CANCEL_STAGES = {"placed", "accepted", "preparing"}  # FR-ORD-04 (fee brackets via refunds later)


def _int(data, key, default=0):
    try:
        return int(data.get(key, default))
    except (TypeError, ValueError):
        raise DomainError("orders.bad_number", f"{key} must be an integer.")


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Order history + place + guarded transitions (FR-ORD-01..08)."""

    serializer_class = OrderSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        user = self.request.user
        base = Order.objects.select_related("branch", "branch__vendor").prefetch_related("items")
        if user.is_staff or user.role == "operator":
            return base
        if user.role == "vendor":
            return (base.filter(branch__vendor__owner=user) | base.filter(branch__staff__user=user))
        return base.filter(customer=user)

    @action(detail=False, methods=["post"])
    def place(self, request):
        """POST /orders/place/ with Idempotency-Key header (FR-ORD-01/02)."""
        address = None
        if ref := request.data.get("address"):
            address = Address.objects.filter(user=request.user, uuid=ref).first()
            if not address:
                raise DomainError("order.address_required", "Unknown delivery address for this account.")
        body, replay = services.place(
            user=request.user, address=address, coupon_code=request.data.get("coupon_code", ""),
            tip_minor=_int(request.data, "tip_minor"), idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        headers = {"Idempotency-Replayed": "true"} if replay else None
        return Response(body, status=status.HTTP_200_OK if replay else status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"])
    def transition(self, request, uuid=None):
        order = self.get_object()
        to_status = request.data.get("to_status", "")
        role = "operator" if request.user.is_staff or request.user.role == "operator" else request.user.role
        if role == "customer":
            if to_status != "cancelled_customer":
                raise DomainError("order.forbidden", "Customers may only cancel orders.", status.HTTP_403_FORBIDDEN)
            if order.status not in CUSTOMER_CANCEL_STAGES:
                raise DomainError("order.cancel_window", "Cancellation is support-ticket-only at this stage.", status.HTTP_409_CONFLICT)
        elif role == "vendor" and to_status not in VENDOR_TARGETS:
            raise DomainError("order.forbidden", "Not a vendor action.", status.HTTP_403_FORBIDDEN)
        elif role == "operator" and not request.data.get("reason"):
            raise DomainError("order.reason_required", "Forced transitions need a reason (FR-ORD-08).")
        if to_status == "accepted":
            order.accepted_by = request.user
        services.transition(order, to_status=to_status, actor_type=role, actor_id=request.user.id,
                            reason=request.data.get("reason", ""))
        return Response(OrderSerializer(order).data)
