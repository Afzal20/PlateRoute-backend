import hashlib
import hmac
import json
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from orders import services as order_services
from orders.models import Order
from payments.models import Invoice, LedgerEntry, Payment
from .helpers import api, make_user
from .test_orders import make_address, seed_cart


class CODFlowTests(TestCase):
    """FR-PAY-01: COD rides the same ledger; capture lands at delivery."""

    def setUp(self):
        self.user = make_user()
        self.branch, self.item = seed_cart(self.user)
        self.address = make_address(self.user)
        api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        self.order = Order.objects.get()

    def _drive_to_delivered(self):
        vendor = self.branch.vendor.owner
        for status in ("accepted", "preparing", "ready"):
            api(vendor, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": status})
        self.order.refresh_from_db()  # vendor moves happened via API
        for status in ("picked", "out", "delivered"):
            order_services.transition(self.order, to_status=status, actor_type="system")

    def test_cod_captured_on_delivery_with_zero_sum_ledger(self):
        res = api(self.user, "post", f"/v1/payments/{self.order.uuid}/start/", {"gateway": "cod"})
        self.assertEqual(res.json()["state"], "initiated")
        # starting twice returns the same live payment
        again = api(self.user, "post", f"/v1/payments/{self.order.uuid}/start/", {"gateway": "cod"})
        self.assertEqual(res.json()["amount_minor"], again.json()["amount_minor"])
        self._drive_to_delivered()
        call_command("pump_outbox")
        self.order.refresh_from_db()
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.state, "captured")
        entries = LedgerEntry.objects.filter(order=self.order)
        self.assertEqual(sum(e.amount_minor for e in entries), 0)  # double-entry balances
        self.assertIn("vendor_settlement", {e.entry_type for e in entries})
        invoice = Invoice.objects.get(order=self.order)
        self.assertTrue(invoice.full_number.startswith(f"BD-{invoice.series}-"))
        status_res = api(self.user, "get", f"/v1/payments/{self.order.uuid}/")
        self.assertEqual(status_res.json()["state"], "captured")


class StripeWebhookTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.branch, self.item = seed_cart(self.user)
        self.address = make_address(self.user)
        api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        self.order = Order.objects.get()
        self.secret = "whsec_test"

    def _signed(self, body: dict, ts=None):
        import time as _time
        raw = json.dumps(body).encode()
        ts = int(_time.time()) if ts is None else int(ts)
        signed = f"{ts}.{raw.decode()}".encode()
        sig = hmac.new(self.secret.encode(), signed, hashlib.sha256).hexdigest()
        return raw, {"X-Signature": f"t={ts},v1={sig}"}

    def test_session_and_webhook_capture(self):
        res = api(self.user, "post", f"/v1/payments/{self.order.uuid}/start/", {"gateway": "stripe"})
        self.assertIn("client_secret", res.json()["session"])
        raw, headers = self._signed({"id": "evt_1", "type": "payment_intent.succeeded", "data": {"reference": str(self.order.uuid)}})
        with mock.patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": self.secret}):
            bad = self.client.post("/api/v1/payments/webhooks/stripe/", raw, content_type="application/json", headers={"X-Signature": "nope"})
            self.assertEqual(bad.status_code, 400)
            ok = self.client.post("/api/v1/payments/webhooks/stripe/", raw, content_type="application/json", headers=headers)
            self.assertEqual(ok.status_code, 200)
            dup = self.client.post("/api/v1/payments/webhooks/stripe/", raw, content_type="application/json", headers=headers)
            self.assertEqual(dup.json(), {"detail": "duplicate"})
        self.assertEqual(Payment.objects.get(order=self.order).state, "captured")

    def test_stale_signature_rejected_as_replay(self):
        raw, headers = self._signed({"id": "evt_r"}, ts=0)  # 1970: far outside the 300s window
        with mock.patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": self.secret}):
            res = self.client.post("/api/v1/payments/webhooks/stripe/", raw, content_type="application/json", headers=headers)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "webhook.signature")

    def test_unknown_provider_and_malformed_json(self):
        with mock.patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": self.secret}):
            unknown = self.client.post("/api/v1/payments/webhooks/crypto-exchange/", b"{}", content_type="application/json", headers={"X-Signature": "x"})
            self.assertEqual(unknown.status_code, 400)
            self.assertEqual(unknown.json()["code"], "webhook.gateway_unknown")
            # malformed JSON must be a 400, never a 500
            malformed = self.client.post("/api/v1/payments/webhooks/stripe/", b"{not json", content_type="application/json", headers={"X-Signature": "t=1234,v1=abcd"})
            self.assertEqual(malformed.status_code, 400)

    def test_refund_flow(self):
        for status in ("accepted", "preparing", "ready"):
            api(self.branch.vendor.owner, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": status})
        self.order.refresh_from_db()  # vendor moves happened via API
        for status in ("picked", "out", "delivered"):
            order_services.transition(self.order, to_status=status, actor_type="system")
        Payment.objects.create(order=self.order, gateway="stripe", amount_minor=self.order.grand_total_minor, state="captured")
        res = api(self.user, "post", "/v1/payments/refunds/", {"order": str(self.order.uuid), "amount_minor": 99999999, "reason": "late"})
        self.assertEqual(res.json()["code"], "refund.too_large")
        res = api(self.user, "post", "/v1/payments/refunds/", {"order": str(self.order.uuid), "amount_minor": 5000, "reason": "late"})
        self.assertEqual(res.status_code, 201)
        operator = make_user("o@test.io", role="operator")
        approve = api(operator, "post", "/v1/payments/refunds/1/approve/")
        self.assertEqual(approve.json()["state"], "succeeded")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "refund_pending")
        self.assertTrue(LedgerEntry.objects.filter(entry_type="refund_out", amount_minor=-5000).exists())
        # customers cannot approve
        self.assertEqual(api(self.user, "post", "/v1/payments/refunds/1/approve/").status_code, 403)