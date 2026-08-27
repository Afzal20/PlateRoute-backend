"""Gateway port (FR-PAY-01). Card data never touches the platform (FR-PAY-02)."""
import hashlib
import hmac
import os

from .models import Payment


class PaymentGateway:
    def create_session(self, payment):
        raise NotImplementedError

    def verify_webhook(self, raw_body, signature):
        raise NotImplementedError


class CodGateway(PaymentGateway):
    """COD is a pseudo-gateway feeding the same ledger; captured at delivery."""

    def create_session(self, payment):
        return {"mode": "cod"}

    def verify_webhook(self, raw_body, signature):
        return False  # no inbound webhooks for cash


class StripeGateway(PaymentGateway):
    """Skeleton: session shape matches the real SDK flow; swap body in M5."""

    def create_session(self, payment):
        return {"mode": "hosted", "client_secret": f"cs_test_{payment.order.uuid}", "amount_minor": payment.amount_minor}

    def verify_webhook(self, raw_body, signature):
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        if not secret:
            return False
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature or "")


def gateway(kind):
    return {"cod": CodGateway, "stripe": StripeGateway, "bkash": StripeGateway, "nagad": StripeGateway}[kind]()
