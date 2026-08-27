from django.test import TestCase

from addresses.models import Address
from carts.models import Cart, CartItem
from common.models import OutboxMessage
from menus.models import Category, Item
from orders.models import Order
from .helpers import api, make_user
from .test_vendors import make_vendor_branch


def seed_cart(user, price=35000, qty=2, owner=None):
    """Fill the user's cart with one line; returns (branch, item)."""
    from uuid import uuid4
    owner = owner or make_user(f"v-{uuid4().hex[:8]}@test.io", role="vendor")
    vendor, branch = make_vendor_branch(owner)
    category = Category.objects.create(branch=branch, name="Biryani")
    item = Item.objects.create(category=category, name="Kacchi", base_price_minor=price)
    cart, _ = Cart.objects.get_or_create(user=user)
    cart.branch = branch
    cart.save()
    CartItem.objects.create(cart=cart, item=item, qty=qty)
    return branch, item


def make_address(user):
    return Address.objects.create(user=user, label="Home", receiver_name="A", phone="017", lat=23.8, lng=90.4, city="Dhaka")


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.branch, self.item = seed_cart(self.user)
        self.address = make_address(self.user)

    def test_place_freezes_prices_and_emits_outbox(self):
        res = api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid)}, headers={"Idempotency-Key": "key-1"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["grand_total_minor"], 70000 + 5000 + 3500)  # items + fee + 5% vat
        order = Order.objects.get()
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().unit_price_minor, 35000)
        self.assertEqual(order.events.count(), 1)
        self.assertTrue(OutboxMessage.objects.filter(kind="order.placed").exists())
        self.assertEqual(CartItem.objects.count(), 0)  # cart cleared

    def test_idempotency_replay(self):
        first = api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid)}, headers={"Idempotency-Key": "k"})
        second = api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid)}, headers={"Idempotency-Key": "k"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OutboxMessage.objects.filter(kind="order.placed").count(), 1)

    def test_coupon_atomic_redemption_and_cap(self):
        from promotions.models import Coupon
        Coupon.objects.create(code="C10", kind="percent", value=1000, ends_at="2099-01-01T00:00:00Z")
        res = api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid), "coupon_code": "C10"})
        order = Order.objects.get()
        self.assertEqual(order.discount_minor, 7000)
        self.assertEqual(order.coupon["code"], "C10")
        seed_cart(self.user)  # second basket against the same coupon hits per_user_limit=1
        res = api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid), "coupon_code": "C10"})
        self.assertEqual(res.json()["code"], "coupon.per_user")

    def test_empty_cart_rejected(self):
        CartItem.objects.all().delete()
        res = api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        self.assertEqual(res.json()["code"], "order.empty_cart")

    def test_other_users_address_rejected(self):
        stranger = make_address(make_user("s@test.io"))
        res = api(self.user, "post", "/v1/orders/place/", {"address": str(stranger.uuid)})
        self.assertEqual(res.json()["code"], "order.address_required")

class TransitionTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.vendor_user = make_user("v@test.io", role="vendor")
        self.branch, self.item = seed_cart(self.user, owner=self.vendor_user)
        self.address = make_address(self.user)
        api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        self.order = Order.objects.get()

    def _vendor_transition(self, to_status, user=None):
        return api(user or self.vendor_user, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": to_status})

    def test_vendor_accept_flow_with_scoping(self):
        self.assertEqual(self._vendor_transition("accepted").status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "accepted")
        self.assertEqual(self.order.accepted_by, self.vendor_user)
        self._vendor_transition("preparing")
        self._vendor_transition("ready")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "ready")

    def test_illegal_transition_rejected(self):
        self.assertEqual(self._vendor_transition("delivered").status_code, 403)  # not a vendor action
        res = self._vendor_transition("preparing")  # vendor action, but state-illegal (skips accept)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "order.illegal_transition")

    def test_customer_cancel_window(self):
        res = api(self.user, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": "cancelled_customer"})
        self.assertEqual(res.status_code, 200)
        res = api(self.user, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": "cancelled_customer"})
        self.assertEqual(res.status_code, 409)  # terminal now

    def test_customer_cannot_accept(self):
        res = api(self.user, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": "accepted"})
        self.assertEqual(res.status_code, 403)

    def test_vendor_scoping_foreign_branch(self):
        other_vendor = make_user("v2@test.io", role="vendor")
        self.assertEqual(self._vendor_transition("accepted", other_vendor).status_code, 404)

    def test_operator_force_needs_reason(self):
        operator = make_user("o@test.io", role="operator")
        no_reason = api(operator, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": "cancelled_platform"})
        self.assertEqual(no_reason.status_code, 400)
        res = api(operator, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": "cancelled_platform", "reason": "fraud check"})
        self.assertEqual(res.status_code, 200)
