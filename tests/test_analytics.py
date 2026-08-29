"""Dedicated test suite for the ``analytics`` app (FR-REP-01..03).

Verifies the nightly aggregate builder (rebuild_daily_metrics command) and
the cheap reads it powers in the merchant-facing branch report, including
the operator/owner permission gate on the endpoint.
"""
from django.core.management import call_command
from django.test import TestCase

from analytics.models import DailyBranchMetrics
from orders.models import Order

from .helpers import api, make_user
from .test_orders import make_address, seed_cart


class AnalyticsTests(TestCase):
    """Daily branch metrics and the FR-REP-02 read endpoint."""

    def setUp(self):
        self.customer = make_user()
        self.branch, _ = seed_cart(self.customer)
        self.address = make_address(self.customer)

    def test_daily_metrics_rebuild_and_report(self):
        api(self.customer, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})

        # The beat equivalent produces exactly one aggregate row for today.
        call_command("rebuild_daily_metrics", "--days", "0")
        self.assertEqual(DailyBranchMetrics.objects.count(), 1)
        metrics = DailyBranchMetrics.objects.get()
        self.assertEqual(metrics.orders_count, 1)
        self.assertEqual(metrics.gmv_minor, Order.objects.get().grand_total_minor)

        # The merchant can read their own report; an outsider (even the
        # customer) cannot access another branch's numbers.
        report = api(self.branch.vendor.owner, "get", f"/v1/reports/branches/{self.branch.uuid}/")
        self.assertEqual(report.json()["orders"], 1)
        self.assertEqual(api(self.customer, "get", f"/v1/reports/branches/{self.branch.uuid}/").status_code, 403)

    def test_rebuild_is_idempotent_same_day(self):
        api(self.customer, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        call_command("rebuild_daily_metrics", "--days", "0")
        call_command("rebuild_daily_metrics", "--days", "0")
        # update_or_create keeps a single per-(date, branch) row.
        self.assertEqual(DailyBranchMetrics.objects.count(), 1)