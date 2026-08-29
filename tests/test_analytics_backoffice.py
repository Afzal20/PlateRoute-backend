from django.core.management import call_command
from django.test import TestCase

from analytics.models import DailyBranchMetrics
from orders.models import Order
from payments.models import Payment, Refund
from .helpers import api, make_user
from .test_orders import make_address, seed_cart


class AnalyticsBackofficeTests(TestCase):
    """FR-REP-01..03 + FR-ADM-02/03: aggregates and the ops console."""

    def setUp(self):
        self.operator = make_user("ops@test.io", role="operator")
        self.customer = make_user()
        self.branch, _ = seed_cart(self.customer)
        self.address = make_address(self.customer)

    def test_daily_metrics_rebuild_and_report(self):
        api(self.customer, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        call_command("rebuild_daily_metrics", "--days", "0")  # today's row
        self.assertEqual(DailyBranchMetrics.objects.count(), 1)
        metrics = DailyBranchMetrics.objects.get()
        self.assertEqual(metrics.orders_count, 1)
        self.assertEqual(metrics.gmv_minor, Order.objects.get().grand_total_minor)
        # merchant reads the report; outsiders cannot
        report = api(self.branch.vendor.owner, "get", f"/v1/reports/branches/{self.branch.uuid}/")
        self.assertEqual(report.json()["orders"], 1)
        self.assertEqual(api(self.customer, "get", f"/v1/reports/branches/{self.branch.uuid}/").status_code, 403)

    def test_ops_board_scoped_to_operators(self):
        api(self.customer, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        self.assertEqual(api(self.customer, "get", "/v1/backoffice/orders/").status_code, 403)
        board = api(self.operator, "get", "/v1/backoffice/orders/").json()
        self.assertEqual(len(board), 1)
        self.assertEqual(board[0]["branch"], self.branch.name)

    def test_refund_queue_approve_and_reject(self):
        api(self.customer, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        order = Order.objects.get()
        # drive to delivered so refunds are legal (FR-PAY-05)
        vendor = self.branch.vendor.owner
        for s in ("accepted", "preparing", "ready"):
            api(vendor, "post", f"/v1/orders/{order.uuid}/transition/", {"to_status": s})
        order.refresh_from_db()
        from orders import services as order_services
        for s in ("picked", "out", "delivered"):
            order_services.transition(order, to_status=s, actor_type="system")
        Payment.objects.create(order=order, gateway="stripe", amount_minor=order.grand_total_minor, state="captured")
        api(self.customer, "post", "/v1/payments/refunds/", {"order": str(order.uuid), "amount_minor": 1000, "reason": "late"})
        queue = api(self.operator, "get", "/v1/backoffice/refunds/").json()
        self.assertEqual(len(queue), 1)
        res = api(self.operator, "post", "/v1/backoffice/refunds/", {"refund_id": queue[0]["id"], "approve": True})
        self.assertEqual(res.json()["state"], "succeeded")
        order.refresh_from_db()
        self.assertEqual(order.status, "refund_pending")
        # reject path on a fresh refund
        api(self.customer, "post", "/v1/payments/refunds/", {"order": str(order.uuid), "amount_minor": 500, "reason": "goodwill"})
        queue = api(self.operator, "get", "/v1/backoffice/refunds/").json()
        res = api(self.operator, "post", "/v1/backoffice/refunds/", {"refund_id": queue[0]["id"], "approve": False})
        self.assertEqual(res.json()["state"], "failed")

    def test_config_bridge(self):
        res = api(self.operator, "post", "/v1/backoffice/config/", {"key": "delivery.fee_minor", "value": 6000})
        self.assertEqual(res.json()["version"], 1)
        res = api(self.operator, "post", "/v1/backoffice/config/", {"key": "delivery.fee_minor", "value": 7000})
        self.assertEqual(res.json()["version"], 2)
        from common.models import RuntimeConfig
        self.assertEqual(RuntimeConfig.get("delivery.fee_minor"), 7000)
        self.assertEqual(api(self.customer, "get", "/v1/backoffice/config/").status_code, 403)