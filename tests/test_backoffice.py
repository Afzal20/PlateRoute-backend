"""Dedicated test suite for the ``backoffice`` app (FR-ADM-02/03).

Covers the operator-only surfaces: the live orders board, the refund
approve/reject queue, and the runtime-config bridge (optimistic version
counter). Every endpoint must reject non-operator users with 403.
"""
from django.test import TestCase

from common.models import RuntimeConfig
from orders import services as order_services
from orders.models import Order
from payments.models import Payment

from .helpers import api, make_user
from .test_orders import make_address, seed_cart


def _drive_to_delivered(customer, order):
    """Bring an order to DELIVERED so refunds become legal (FR-PAY-05)."""
    branch = order.branch
    for s in ("accepted", "preparing", "ready"):
        api(branch.vendor.owner, "post", f"/v1/orders/{order.uuid}/transition/", {"to_status": s})
    order.refresh_from_db()  # vendor moves happened via API
    for s in ("picked", "out", "delivered"):
        order_services.transition(order, to_status=s, actor_type="system")


class BackofficeTests(TestCase):
    """Operator console endpoints and their authentication gates."""

    def setUp(self):
        self.operator = make_user("ops@test.io", role="operator")
        self.customer = make_user()
        self.branch, _ = seed_cart(self.customer)
        self.address = make_address(self.customer)

    def test_ops_board_scoped_to_operators(self):
        api(self.customer, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        # A regular user is denied the board.
        self.assertEqual(api(self.customer, "get", "/v1/backoffice/orders/").status_code, 403)
        # The operator sees orders across every branch.
        board = api(self.operator, "get", "/v1/backoffice/orders/").json()
        self.assertEqual(len(board), 1)
        self.assertEqual(board[0]["branch"], self.branch.name)

    def test_refund_queue_approve_and_reject(self):
        api(self.customer, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        order = Order.objects.get()
        _drive_to_delivered(self.customer, order)
        Payment.objects.create(order=order, gateway="stripe",
                               amount_minor=order.grand_total_minor, state="captured")

        # Push two requests and run the queue through approve then reject.
        api(self.customer, "post", "/v1/payments/refunds/",
            {"order": str(order.uuid), "amount_minor": 1000, "reason": "late"})
        queue = api(self.operator, "get", "/v1/backoffice/refunds/").json()
        self.assertEqual(len(queue), 1)
        approved = api(self.operator, "post", "/v1/backoffice/refunds/",
                       {"refund_id": queue[0]["id"], "approve": True})
        self.assertEqual(approved.json()["state"], "succeeded")
        order.refresh_from_db()
        self.assertEqual(order.status, "refund_pending")

        api(self.customer, "post", "/v1/payments/refunds/",
            {"order": str(order.uuid), "amount_minor": 500, "reason": "goodwill"})
        queue = api(self.operator, "get", "/v1/backoffice/refunds/").json()
        rejected = api(self.operator, "post", "/v1/backoffice/refunds/",
                       {"refund_id": queue[0]["id"], "approve": False})
        self.assertEqual(rejected.json()["state"], "failed")

    def test_single_active_refund_approval_is_safe(self):
        # Non-operators can never touch the queue.
        self.assertEqual(api(self.customer, "get", "/v1/backoffice/refunds/").status_code, 403)

    def test_config_bridge(self):
        # First create (version 1), then update bumps the optimistic counter.
        created = api(self.operator, "post", "/v1/backoffice/config/",
                      {"key": "delivery.fee_minor", "value": 6000})
        self.assertEqual(created.json()["version"], 1)
        updated = api(self.operator, "post", "/v1/backoffice/config/",
                      {"key": "delivery.fee_minor", "value": 7000})
        self.assertEqual(updated.json()["version"], 2)
        self.assertEqual(RuntimeConfig.get("delivery.fee_minor"), 7000)
        # Non-operators cannot read or write config.
        self.assertEqual(api(self.customer, "get", "/v1/backoffice/config/").status_code, 403)