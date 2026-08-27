"""Money movement services: start/capture, ledger pairs, refunds, invoices."""
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from common.errors import DomainError
from common.money import bp_of

from .gateways import gateway
from .models import Invoice, LedgerEntry, Payment, Refund


@transaction.atomic
def start(order, *, gateway_name):
    """Return the live payment for the order plus a client session payload."""
    existing = getattr(order, "payment", None)
    if existing and existing.state in (Payment.State.INITIATED, Payment.State.AUTHORIZED, Payment.State.REQUIRES_ACTION):
        if existing.gateway == gateway_name:
            return existing, gateway(gateway_name).create_session(existing)
        raise DomainError("payment.live_exists", "Cancel or complete the current payment first.", 409)
    payment = Payment.objects.create(order=order, gateway=gateway_name, amount_minor=order.grand_total_minor)
    return payment, gateway(gateway_name).create_session(payment)


@transaction.atomic
def capture(payment, *, payment_ref=""):
    """Settle a payment: state, ledger pair (zero-sum), invoice, outbox."""
    if payment.state == Payment.State.CAPTURED:
        return payment  # idempotent
    payment.state = Payment.State.CAPTURED
    payment.captured_at = timezone.now()
    payment.gateway_reference = payment.gateway_reference or payment_ref
    payment.save(update_fields=["state", "captured_at", "gateway_reference"])
    order = payment.order
    commission = bp_of(order.items_total_minor, order.branch.vendor.commission_bp)
    batch = uuid4()
    order_uuid = str(order.uuid)
    LedgerEntry.objects.bulk_create([
        LedgerEntry(entry_type=LedgerEntry.EntryType.ORDER_CAPTURE, order=order, payee_type="platform",
                    amount_minor=payment.amount_minor, currency=payment.currency, batch_uuid=batch),
        LedgerEntry(entry_type=LedgerEntry.EntryType.VENDOR_SETTLEMENT, order=order, payee_type="vendor",
                    payee_id=order.branch.vendor_id, amount_minor=-(payment.amount_minor - commission),
                    currency=payment.currency, batch_uuid=batch),
        LedgerEntry(entry_type=LedgerEntry.EntryType.PLATFORM_COMMISSION, order=order, payee_type="platform",
                    amount_minor=-commission, currency=payment.currency, batch_uuid=batch),
    ])
    invoice, _ = Invoice.objects.get_or_create(order=order, series=str(timezone.now().year))
    invoice.save()  # assigns number/full_number on first save
    from common.models import OutboxMessage
    OutboxMessage.emit("payment.captured", order=order_uuid, invoice=invoice.full_number,
                       amount_minor=payment.amount_minor, gateway=payment.gateway)
    return payment


@transaction.atomic
def settle_cod_on_delivery(order):
    """Outbox handler: COD captured when the order is delivered (§8.9)."""
    payment = Payment.objects.filter(order=order, gateway=Payment.Gateway.COD).first()
    if payment and payment.state != Payment.State.CAPTURED:
        capture(payment, payment_ref=f"cod-{order.pk}")


@transaction.atomic
def request_refund(order, *, user, amount_minor, reason):
    payment = getattr(order, "payment", None)
    if not payment or payment.state != Payment.State.CAPTURED:
        raise DomainError("refund.not_capturable", "Only captured payments can be refunded.")
    if amount_minor > payment.amount_minor:
        raise DomainError("refund.too_large", "Refund exceeds the captured amount.")
    return Refund.objects.create(payment=payment, amount_minor=amount_minor, reason=reason, requested_by=user)


@transaction.atomic
def approve_refund(refund, *, operator):
    from orders.services import transition
    refund.state = Refund.State.SUCCEEDED
    refund.approved_by = operator
    refund.processed_at = timezone.now()
    refund.save(update_fields=["state", "approved_by", "processed_at"])
    LedgerEntry.objects.create(entry_type=LedgerEntry.EntryType.REFUND_OUT, order=refund.payment.order,
                               payee_type="platform", amount_minor=-refund.amount_minor,
                               currency=refund.payment.currency, batch_uuid=uuid4())
    order = refund.payment.order
    target = "refund_pending" if order.status == "delivered" else "refunded"
    if order.status != "refunded":
        transition(order, to_status=target, actor_type="operator", actor_id=operator.id, reason="refund approved")
    return refund
