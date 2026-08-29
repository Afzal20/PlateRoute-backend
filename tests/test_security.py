from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from accounts.models import Profile
from orders import services as order_services
from orders.models import Order
from payments.models import Invoice, LedgerEntry, Payment
from .helpers import api, make_user
from .test_orders import make_address, seed_cart


class SecurityRegressionTests(TestCase):
    """Regression tests for the security hardening pass."""

    def test_profile_patch_cannot_escalate_role(self):
        user = make_user()
        res = api(user, "patch", "/auth/profile/", {"role": "operator"})
        self.assertEqual(res.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.role, "customer")  # role is read-only on profile

    def test_email_change_requires_current_password(self, ):
        user = make_user()
        res = api(user, "patch", "/auth/profile/", {"email": "new@test.io"})
        self.assertEqual(res.status_code, 400)  # no current_password
        res = api(user, "patch", "/auth/profile/", {"email": "new@test.io", "current_password": "wrong"})
        self.assertEqual(res.status_code, 400)
        profile, _ = Profile.objects.get_or_create(user=user)
        before = profile.token_version
        res = api(user, "patch", "/auth/profile/", {"email": "new@test.io", "current_password": "Str0ngPass!x"})
        self.assertEqual(res.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.email, "new@test.io")
        profile.refresh_from_db()
        self.assertGreater(profile.token_version, before)  # sessions invalidated

    def test_unknown_gateway_rejected(self):
        user = make_user()
        branch, _ = seed_cart(user)
        address = make_address(user)
        api(user, "post", "/v1/orders/place/", {"address": str(address.uuid)})
        order = Order.objects.get()
        res = api(user, "post", f"/v1/payments/{order.uuid}/start/", {"gateway": "not-a-gateway"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "payment.gateway_unknown")

    def test_refund_rejects_non_int_amount(self):
        user = make_user()
        branch, _ = seed_cart(user)
        address = make_address(user)
        api(user, "post", "/v1/orders/place/", {"address": str(address.uuid)})
        order = Order.objects.get()
        Payment.objects.create(order=order, gateway="stripe", amount_minor=order.grand_total_minor, state="captured")
        res = api(user, "post", "/v1/payments/refunds/", {"order": str(order.uuid), "amount_minor": "not-int", "reason": "late"})
        self.assertEqual(res.status_code, 400)

    def test_coupon_unknown_and_bad_subtotal(self):
        user = make_user()
        self.assertEqual(api(user, "post", "/v1/coupons/validate/", {"code": "NOPE", "subtotal_minor": 100}).status_code, 404)
        from .test_promotions import make_coupon
        make_coupon("SAVE10")
        self.assertEqual(api(user, "post", "/v1/coupons/validate/", {"code": "SAVE10", "subtotal_minor": "x"}).status_code, 400)

    def test_non_participant_payment_lookup_hides_existence(self):
        user = make_user()
        victim = make_user("victim@test.io")
        branch, _ = seed_cart(victim)
        address = make_address(victim)
        api(victim, "post", "/v1/orders/place/", {"address": str(address.uuid)})
        order = Order.objects.get(customer=victim)
        res = api(user, "post", f"/v1/payments/{order.uuid}/start/", {"gateway": "cod"})
        self.assertEqual(res.status_code, 404)  # no existence oracle