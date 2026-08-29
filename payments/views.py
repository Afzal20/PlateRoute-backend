import json

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError
from orders.models import Order

from . import services
from .gateways import gateway
from .models import Payment, Refund, WebhookEvent


def _positive_int(value, default=0, code="input.bad_number"):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise DomainError(code, f"{code} must be an integer.", status.HTTP_400_BAD_REQUEST)
    return max(parsed, 0)


def _participant_order(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid)
    is_operator = request.user.is_staff or request.user.role == "operator"
    if order.customer_id != request.user.id and not is_operator:
        # 404 (not 403) so the endpoint cannot confirm that other users'
        # order UUIDs exist (avoid an existence oracle).
        raise DomainError("payment.forbidden", "Not your order.", status.HTTP_404_NOT_FOUND)
    return order


class PaymentStartView(APIView):
    """POST /payments/{order_uuid}/start -> live payment + client session."""

    def post(self, request, order_uuid):
        order = _participant_order(request, order_uuid)
        kind = request.data.get("gateway", "cod")
        payment, session = services.start(order, gateway_name=kind)
        return Response({"gateway": payment.gateway, "state": payment.state, "amount_minor": payment.amount_minor,
                         "session": session})


class PaymentStatusView(APIView):
    def get(self, request, order_uuid):
        order = _participant_order(request, order_uuid)
        payment = getattr(order, "payment", None)
        return Response({"order": str(order.uuid), "state": payment.state if payment else "unpaid",
                         "gateway": payment.gateway if payment else None})


class WebhookView(APIView):
    """FR-PAY-03: verify HMAC, dedupe by event id, process after fast-ack."""

    permission_classes = (permissions.AllowAny,)

    def post(self, request, provider):
        raw = request.body
        adapter = gateway(provider)
        if adapter is None:
            raise DomainError("webhook.gateway_unknown", "Unknown gateway.", status.HTTP_400_BAD_REQUEST)
        if not adapter.verify_webhook(raw, request.headers.get("X-Signature")):
            raise DomainError("webhook.signature", "Invalid webhook signature.", status.HTTP_400_BAD_REQUEST)
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            raise DomainError("webhook.bad_json", "Malformed payload.", status.HTTP_400_BAD_REQUEST)
        event, created = WebhookEvent.objects.get_or_create(
            provider=provider, event_id=body.get("id", ""), defaults={"payload": body})
        if not created:
            return Response({"detail": "duplicate"}, status=status.HTTP_200_OK)
        if body.get("type") == "payment_intent.succeeded":
            payment = Payment.objects.filter(order__uuid=body.get("data", {}).get("reference", "")).first()
            if payment:
                services.capture(payment, payment_ref=body["id"])
                event.state = WebhookEvent.State.PROCESSED
            else:
                event.state = WebhookEvent.State.IGNORED
        else:
            event.state = WebhookEvent.State.IGNORED
        event.save(update_fields=["state"])
        return Response({"detail": "ok"})


class RefundRequestView(APIView):
    """POST /payments/refunds — customer asks for money back (FR-PAY-05)."""

    def post(self, request):
        order = _participant_order(request, request.data.get("order", ""))
        amount = _positive_int(request.data.get("amount_minor"), code="refund.amount_must_be_int")
        refund = services.request_refund(order, user=request.user, amount_minor=amount,
                                         reason=request.data.get("reason", Refund.Reason.MISTAKE))
        return Response({"id": refund.id, "state": refund.state, "amount_minor": refund.amount_minor}, status=status.HTTP_201_CREATED)


class RefundApproveView(APIView):
    def post(self, request, pk):
        if not (request.user.is_staff or request.user.role == "operator"):
            raise DomainError("refund.forbidden", "Operators approve refunds.", status.HTTP_403_FORBIDDEN)
        refund = get_object_or_404(Refund, pk=pk)
        services.approve_refund(refund, operator=request.user)
        return Response({"id": refund.id, "state": refund.state})
