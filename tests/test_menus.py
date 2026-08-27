from django.test import TestCase

from menus.models import Category, Item
from vendors.models import Branch, Vendor
from .helpers import api, make_user
from .test_vendors import make_vendor_branch


def make_item(category, name="Kacchi Full", price=35000, **kw):
    return Item.objects.create(category=category, name=name, base_price_minor=price, **kw)


class MenuTests(TestCase):
    def setUp(self):
        self.vendor_user = make_user("v@test.io", role="vendor")
        self.other_vendor = make_user("v2@test.io", role="vendor")
        self.customer = make_user("c@test.io")
        self.vendor, self.branch = make_vendor_branch(self.vendor_user)

    def test_category_and_nested_item_write(self):
        res = api(self.vendor_user, "post", "/v1/menu/categories/", {"branch": str(self.branch.uuid), "name": "Biryani"})
        self.assertEqual(res.status_code, 201)
        cat_uuid = res.json()["uuid"]
        payload = {
            "category": cat_uuid,
            "name": "Kacchi",
            "base_price_minor": 35000,
            "groups": [
                {"title": "Spice", "min_select": 1, "max_select": 1,
                 "options": [{"label": "Hot"}, {"label": "Mild", "is_default": True}]},
            ],
        }
        res = api(self.vendor_user, "post", "/v1/menu/items/", payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["groups"][0]["options"][1]["label"], "Mild")
        self.assertEqual(res.json()["branch"], str(self.branch.uuid))

    def test_role_and_scoping(self):
        category = Category.objects.create(branch=self.branch, name="Starters")
        _, other_branch = make_vendor_branch(self.other_vendor)
        # customers cannot write menu
        self.assertEqual(api(self.customer, "post", "/v1/menu/categories/", {"branch": str(self.branch.uuid), "name": "X"}).status_code, 403)
        # other vendor cannot see my items
        make_item(category)
        res = api(self.other_vendor, "get", "/v1/menu/items/")
        self.assertEqual(len(res.json()["results"]), 0)
        # foreign category rejected on create
        res = api(self.other_vendor, "post", "/v1/menu/items/", {"category": str(category.uuid), "name": "Steal", "base_price_minor": 1})
        self.assertEqual(res.status_code, 400)

    def test_toggle_availability(self):
        category = Category.objects.create(branch=self.branch, name="Drinks")
        item = make_item(category, "Borhani")
        res = api(self.vendor_user, "post", f"/v1/menu/items/{item.uuid}/toggle/")
        self.assertFalse(res.json()["available"])
