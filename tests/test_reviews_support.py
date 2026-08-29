from django.test import TestCase

from menus.models import Item
from orders.models import Order
from reviews.models import Review
from .helpers import api, make_user
from .test_orders import make_address, seed_cart


def reviewable_order(customer):
    """Delivered order owned by customer (no review yet)."""
    from orders import services as order_services
    branch, _ = seed_cart(customer)
    address = make_address(customer)
    api(customer, "post", "/v1/orders/place/", {"address": str(address.uuid)})
    order = Order.objects.get(customer=customer)
    for s in ("accepted", "preparing", "ready"):
        api(branch.vendor.owner, "post", f"/v1/orders/{order.uuid}/transition/", {"to_status": s})
    order.refresh_from_db()
    for s in ("picked", "out", "delivered"):
        order_services.transition(order, to_status=s, actor_type="system")
    order.refresh_from_db()
    return branch, order


class ReviewTests(TestCase):
    def test_submit_updates_branch_aggregate_and_reply(self):
        customer = make_user()
        branch, order = reviewable_order(customer)
        res = api(customer, "post", "/v1/reviews/", {"order": str(order.uuid), "restaurant_stars": 4, "body": "Great kacchi"})
        self.assertEqual(res.status_code, 201)
        branch.refresh_from_db()
        self.assertEqual(branch.avg_rating, 4)
        self.assertEqual(branch.rating_count, 1)
        vendor = branch.vendor.owner
        reply = api(vendor, "post", "/v1/reviews/1/reply/", {"body": "Thanks!"})
        self.assertEqual(reply.status_code, 201)
        listed = api(None, "get", f"/v1/reviews/branches/{branch.uuid}/")
        self.assertEqual(listed.json()[0]["reply"], "Thanks!")

    def test_rules(self):
        customer = make_user()
        branch, order = reviewable_order(customer)
        # only the owner may review
        stranger = make_user("s@test.io")
        self.assertEqual(api(stranger, "post", "/v1/reviews/", {"order": str(order.uuid)}).status_code, 403)
        # double submit rejected
        api(customer, "post", "/v1/reviews/", {"order": str(order.uuid)})
        self.assertEqual(api(customer, "post", "/v1/reviews/", {"order": str(order.uuid)}).status_code, 409)


from django.test import TestCase as _T


class SupportTests(_T):
    def test_ticket_open_and_operator_visibility(self):
        customer = make_user()
        branch, order = reviewable_order(customer)
        res = api(customer, "post", "/v1/support/tickets/", {"subject": "Late order", "category": "order_issue", "order": str(order.uuid), "message": "Where is it?"})
        self.assertEqual(res.status_code, 201)
        uuid = res.json()["uuid"]
        operator = make_user("o@test.io", role="operator")
        history = api(operator, "get", f"/v1/support/tickets/{uuid}/")
        self.assertEqual(history.json()["status"], "open")
        self.assertEqual(len(history.json()["messages"]), 1)
        # operator adds an internal note and resolves
        api(operator, "post", f"/v1/support/tickets/{uuid}/", {"message": "refund approved", "internal_note": True, "status": "resolved"})
        customer_view = api(customer, "get", f"/v1/support/tickets/{uuid}/").json()
        self.assertEqual(customer_view["status"], "resolved")
        self.assertFalse(any(m["internal"] for m in customer_view["messages"]))  # internal note hidden

    def test_ticket_scoping(self):
        customer = make_user()
        branch, order = reviewable_order(customer)
        ticket = api(customer, "post", "/v1/support/tickets/", {"subject": "x"}).json()["uuid"]
        stranger = make_user("t@test.io")
        self.assertEqual(api(stranger, "get", f"/v1/support/tickets/{ticket}/").status_code, 403)