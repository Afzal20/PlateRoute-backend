from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError
from common.models import RuntimeConfig
from common.permissions import role_required
from orders.models import Order
from payments.models import Refund
from payments.services import approve_refund


def operator_only(request):
    if not (request.user.is_staff or request.user.role == "operator"):
        raise DomainError("ops.forbidden", "Operators only.", status.HTTP_403_FORBIDDEN)


class OrdersBoardView(APIView):
    """FR-ADM-02: live orders board across every branch."""

    def get(self, request):
        operator_only(request)
        orders = Order.objects.select_related("branch", "customer").order_by("-placed_at")[:200]
        if status_filter := request.GET.get("status"):
            orders = orders.filter(status=status_filter)
        return Response([{
            "uuid": str(o.uuid), "status": o.status, "branch": o.branch.name,
            "customer": o.customer.email, "total_minor": o.grand_total_minor,
            "placed_at": o.placed_at, "payment": getattr(o, "payment", None) and o.payment.state,
        } for o in orders])


class RefundQueueView(APIView):
    """FR-ADM-02: pending refunds awaiting operator approval (FR-PAY-05)."""

    def get(self, request):
        operator_only(request)
        rows = Refund.objects.filter(state=Refund.State.REQUESTED).select_related("payment__order")
        return Response([{"id": r.id, "order": str(r.payment.order.uuid), "amount_minor": r.amount_minor,
                          "reason": r.reason, "requested_by": r.requested_by.email} for r in rows])

    def post(self, request):
        """POST {refund_id, approve: true|false} — approve or reject in one hop."""
        operator_only(request)
        refund = get_object_or_404(Refund, pk=request.data.get("refund_id"))
        if request.data.get("approve"):
            approve_refund(refund, operator=request.user)
            return Response({"id": refund.id, "state": refund.state})
        refund.state = Refund.State.FAILED
        refund.approved_by = request.user
        refund.save(update_fields=["state", "approved_by"])
        return Response({"id": refund.id, "state": refund.state})


class ConfigBridgeView(APIView):
    """FR-ADM-03: runtime config CRUD without redeploy (cached 30s reads)."""

    def get(self, request):
        operator_only(request)
        return Response([{ "key": c.key, "value": c.value, "version": c.version, "description": c.description}
                         for c in RuntimeConfig.objects.order_by("key")])

    def post(self, request):
        operator_only(request)
        key = (request.data.get("key") or "").strip()
        if not key:
            raise DomainError("ops.config_key", "key is required.")
        row, created = RuntimeConfig.objects.get_or_create(key=key, defaults={"value": request.data.get("value", {})})
        row.value = request.data.get("value", row.value)
        if request.data.get("description"):
            row.description = request.data["description"]
        if not created:  # fresh rows already start at version 1
            row.version += 1
        row.save()
        return Response({"key": row.key, "value": row.value, "version": row.version, "created": created})