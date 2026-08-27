from django.test import TestCase

from carts.pricing_service import quote
from common.money import bp_of
from menus.models import Category, Item, Option, OptionGroup
from .helpers import api, make_user
from .test_vendors import make_vendor_branch


def make_option_group(item, title="Spice", min_select=0, max_select=2):
    group = OptionGroup.objects.create(item=item, title=title, min_select=min_select, max_select=max_select)
    hot = Option.objects.create(group=group, label="Hot", price_delta_minor=500)
    extra = Option.objects.create(group=group, label="Extra", price_delta_minor=1500)
    return group, hot, extra


class PricingServiceTests(TestCase):
    def test_invariants_parts_sum_to_total_and_never_negative(self):
        data = quote(lines=[{"line_total_minor": 35000}, {"line_total_minor": 12000}],
                     coupon=(5000, False), delivery_fee_minor=5000, tip_minor=2000)
        self.assertEqual(data["grand_total_minor"],
                         data["items_total_minor"] - data["discount_minor"] + data["delivery_fee_minor"] + data["vat_minor"] + data["tip_minor"])
        self.assertGreaterEqual(data["grand_total_minor"], 0)
        self.assertEqual(data["vat_minor"], bp_of(42000, 500))  # 5% of (items - discount), half-up

    def test_free_delivery_coupon_waives_fee(self):
        data = quote(lines=[{"line_total_minor": 1000}], coupon=(0, True), delivery_fee_minor=5000)
        self.assertEqual(data["delivery_fee_minor"], 0)

    def test_half_up_rounding(self):
        # 5% of 11 minor = 0.55 -> rounds to 1
        data = quote(lines=[{"line_total_minor": 11}], delivery_fee_minor=0, vat_bp=500)
        self.assertEqual(data["vat_minor"], 1)

    def test_empty_lines_zero_total(self):
        data = quote(lines=[], delivery_fee_minor=5000)
        self.assertEqual(data["items_total_minor"], 0)
        self.assertEqual(data["grand_total_minor"], 5000)


class CartFlowTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.vendor, self.branch = make_vendor_branch(make_user("v@test.io", role="vendor"))
        self.category = Category.objects.create(branch=self.branch, name="Biryani")
        self.item = self._make_item()

    def _make_item(self, name="Kacchi", price=35000, **kw):
        return Item.objects.create(category=self.category, name=name, base_price_minor=price, **kw)

    def test_add_line_with_options_and_quote(self):
        group, hot, extra = make_option_group(self.item, min_select=1)
        res = api(self.user, "post", "/v1/carts/items/", {
            "item": str(self.item.uuid), "qty": 2,
            "selected_options": [{"group_id": group.id, "option_id": hot.id}],
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["line_total_minor"], (35000 + 500) * 2)
        data = api(self.user, "get", "/v1/carts/").json()
        self.assertEqual(data["items_total_minor"], 71000)
        self.assertEqual(data["meets_minimum"], True)

    def test_group_rule_violation(self):
        group, hot, extra = make_option_group(self.item, min_select=2)
        res = api(self.user, "post", "/v1/carts/items/", {
            "item": str(self.item.uuid), "qty": 1,
            "selected_options": [{"group_id": group.id, "option_id": hot.id}],
        })
        self.assertEqual(res.json()["code"], "cart.group_rules")

    def test_foreign_and_unavailable_options_rejected(self):
        group, hot, extra = make_option_group(self.item)
        other_item = self._make_item("Fanta", 8000)
        res = api(self.user, "post", "/v1/carts/items/", {
            "item": str(other_item.uuid),
            "selected_options": [{"group_id": group.id, "option_id": hot.id}],
        })
        self.assertEqual(res.json()["code"], "cart.option_invalid")

    def test_cross_branch_conflict_and_replace(self):
        other_vendor, other_branch = make_vendor_branch(make_user("v2@test.io", role="vendor"))
        other_cat = Category.objects.create(branch=other_branch, name="Mains")
        other_item = Item.objects.create(category=other_cat, name="Pizza", base_price_minor=90000)
        api(self.user, "post", "/v1/carts/items/", {"item": str(self.item.uuid)})
        res = api(self.user, "post", "/v1/carts/items/", {"item": str(other_item.uuid)})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "cart.branch_conflict")
        res = api(self.user, "post", "/v1/carts/items/", {"item": str(other_item.uuid), "replace": True})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(api(self.user, "get", "/v1/carts/").json()["items"]), 1)

    def test_qty_update_and_remove_and_clear(self):
        line = api(self.user, "post", "/v1/carts/items/", {"item": str(self.item.uuid)}).json()
        res = api(self.user, "patch", f"/v1/carts/items/{line['id']}/", {"qty": 3})
        self.assertEqual(res.json()["line_total_minor"], 105000)
        api(self.user, "delete", f"/v1/carts/items/{line['id']}/")
        self.assertEqual(api(self.user, "get", "/v1/carts/").json()["items"], [])
        api(self.user, "post", "/v1/carts/items/", {"item": str(self.item.uuid), "qty": 2})
        api(self.user, "post", "/v1/carts/clear/")
        data = api(self.user, "get", "/v1/carts/").json()
        self.assertEqual(data["items_total_minor"], 0)
        self.assertIsNone(data["branch"])
