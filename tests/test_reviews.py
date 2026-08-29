"""Dedicated test suite for the ``reviews`` app.

FR-RVW-01: one review per completed order (owner-only, single-shot),
FR-RVW-02: single restaurant reply per review,
FR-RVW-03: branch rating aggregates maintained on write (never on read).
"""
from django.test import TestCase

from orders import services as order_services
from orders.models import Order
from reviews.models import Review

from .helpers import api, make_user
from .test_orders import make_address, seed_cart


def reviewable_order(customer):
    """Drive one of ``customer``'s orders all the way to DELIVERED.

    Reviews can only be written for delivered orders (FR-RVW-01), so this
    helper performs the allowed vendor moves via the API and the courier-
    owned "picked/out/delivered" legs straight through the order service.
    Returns ``(branch, order)``.
    """
    branch, _ = seed_cart(customer)
    address = make_address(customer)
    api(customer, "post", "/v1/orders/place/", {"address": str(address.uuid)})
    order = Order.objects.get(customer=customer)

    for s in ("accepted", "preparing", "ready"):
        api(branch.vendor.owner, "post", f"/v1/orders/{order.uuid}/transition/", {"to_status": s})
    order.refresh_from_db()  # vendor moves happened via API
    for s in ("picked", "out", "delivered"):
        order_services.transition(order, to_status=s, actor_type="system")
    order.refresh_from_db()
    return branch, order


class ReviewTests(TestCase):
    """Review lifecycle and the FR-RVW-03 aggregate maintenance."""

    def test_submit_updates_branch_aggregate_and_reply(self):
        customer = make_user()
        branch, order = reviewable_order(customer)

        # Writing a review recomputes the branch's denormalized rating.
        res = api(customer, "post", "/v1/reviews/",
                  {"order": str(order.uuid), "restaurant_stars": 4, "body": "Great kacchi"})
        self.assertEqual(res.status_code, 201)
        branch.refresh_from_db()
        self.assertEqual(branch.avg_rating, 4)
        self.assertEqual(branch.rating_count, 1)

        # The merchant (branch staff) can post exactly one reply.
        vendor = branch.vendor.owner
        reply = api(vendor, "post", "/v1/reviews/1/reply/", {"body": "Thanks!"})
        self.assertEqual(reply.status_code, 201)
        listed = api(None, "get", f"/v1/reviews/branches/{branch.uuid}/")
        self.assertEqual(listed.json()[0]["reply"], "Thanks!")

    def test_rules(self):
        customer = make_user()
        branch, order = reviewable_order(customer)

        # Only the order's owner may review it.
        stranger = make_user("s@test.io")
        res = api(stranger, "post", "/v1/reviews/", {"order": str(order.uuid)})
        self.assertEqual(res.status_code, 403)

        # Reviews are single-shot per order; a repeat submit is rejected.
        api(customer, "post", "/v1/reviews/", {"order": str(order.uuid)})
        res = api(customer, "post", "/v1/reviews/", {"order": str(order.uuid)})
        self.assertEqual(res.status_code, 409)

    def test_non_delivered_orders_cannot_be_reviewed(self):
        from .test_orders import make_address, seed_cart  # local import keeps clarity
        customer = make_user()
        branch, _ = seed_cart(customer)
        address = make_address(customer)
        api(customer, "post", "/v1/orders/place/", {"address": str(address.uuid)})
        order = Order.objects.get(customer=customer)  # still in PLACED state
        res = api(customer, "post", "/v1/reviews/",
                  {"order": str(order.uuid), "restaurant_stars": 5})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "review.not_delivered")