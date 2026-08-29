"""Gateway port (FR-PAY-01). Card data never touches the platform (FR-PAY-02)."""
import hashlib
import hmac
import os
import time

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
    """Stripe's timestamped scheme: t=...,v1=... HMAC over ``t.body``.

    The timestamp window defeats replay; compare_digest avoids timing leaks.
    """

    REPLAY_TOLERANCE_SECONDS = 300

    def create_session(self, payment):
        return {"mode": "hosted", "client_secret": f"cs_test_{payment.order.uuid}", "amount_minor": payment.amount_minor}

    def verify_webhook(self, raw_body, signature, timestamp=None):
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        if not secret or not signature:
            return False
        parts = dict(
            (item.split("=", 1) for item in signature.split(",") if "=" in item)
        )
        ts, expected = parts.get("t"), parts.get("v1")
        if not ts or not expected:
            return False
        try:
            ts_i = int(ts)
        except ValueError:
            return False
        if abs((timestamp or int(time.time())) - ts_i) > self.REPLAY_TOLERANCE_SECONDS:
            return False  # stale signature: replay
        signed = f"{ts_i}.{raw_body.decode()}".encode()
        return hmac.compare_digest(hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest(), expected)


def gateway(kind):
    """Return an adapter instance for ``kind`` or None (deny by default)."""
    cls = {"cod": CodGateway, "stripe": StripeGateway, "bkash": StripeGateway, "nagad": StripeGateway}.get(kind)
    return cls() if cls else None
