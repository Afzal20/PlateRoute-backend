"""Dedicated test suite for the ``support`` app (FR-RVW-04 / FR-AUTH-12).

Covers the ticket lifecycle: opening, the operator work queue (internal
notes visible only to operators), status resolution, and strict per-user
scoping so customers cannot read or mutate each other's tickets.
"""
from django.test import TestCase

from .helpers import api, make_user
from .test_orders import make_address, seed_cart
from .test_reviews import reviewable_order


class SupportTests(TestCase):
    """Tickets, operator-only internal notes, and ownership scoping."""

    def test_ticket_open_and_operator_visibility(self):
        customer = make_user()
        branch, order = reviewable_order(customer)

        # Customer opens a ticket linked to their delivered order.
        res = api(customer, "post", "/v1/support/tickets/",
                  {"subject": "Late order", "category": "order_issue",
                   "order": str(order.uuid), "message": "Where is it?"})
        self.assertEqual(res.status_code, 201)
        uuid = res.json()["uuid"]

        operator = make_user("o@test.io", role="operator")
        history = api(operator, "get", f"/v1/support/tickets/{uuid}/")
        self.assertEqual(history.json()["status"], "open")
        self.assertEqual(len(history.json()["messages"]), 1)

        # The operator drops an internal note and resolves the ticket.
        api(operator, "post", f"/v1/support/tickets/{uuid}/",
            {"message": "refund approved", "internal_note": True, "status": "resolved"})

        # The customer sees the resolved status but never the internal note.
        customer_view = api(customer, "get", f"/v1/support/tickets/{uuid}/").json()
        self.assertEqual(customer_view["status"], "resolved")
        self.assertFalse(any(m["internal"] for m in customer_view["messages"]))

    def test_ticket_scoping(self):
        customer = make_user()
        branch, order = reviewable_order(customer)
        ticket = api(customer, "post", "/v1/support/tickets/", {"subject": "x"}).json()["uuid"]

        # Another user cannot read someone else's ticket.
        stranger = make_user("t@test.io")
        self.assertEqual(api(stranger, "get", f"/v1/support/tickets/{ticket}/").status_code, 403)

    def test_linking_another_users_order_is_rejected(self):
        customer = make_user()
        reviewable_order(customer)
        order = customer.orders.first()
        attacker = make_user("attacker@test.io")
        res = api(attacker, "post", "/v1/support/tickets/",
                  {"subject": "hi", "order": str(order.uuid)})
        # A foreign (but real) order uuid must not let an attacker attach to it.
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["code"], "ticket.forbidden")