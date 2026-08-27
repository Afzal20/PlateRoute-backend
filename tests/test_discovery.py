from django.core.cache import cache
from django.test import TestCase

from menus.models import Category
from vendors.models import Vendor
from .helpers import api, make_user
from .test_menus import make_item
from .test_vendors import make_vendor_branch


class DiscoveryTests(TestCase):
    def setUp(self):
        self.owner = make_user("v@test.io", role="vendor")
        self.vendor, self.branch = make_vendor_branch(self.owner)  # approved by default
        cat = Category.objects.create(branch=self.branch, name="Biryani")
        self.item = make_item(cat)

    def _invalidate(self):
        cache.clear()  # menu/list caches are 60s; tests need fresh reads

    def test_public_list_and_search(self):
        self._invalidate()
        res = api(None, "get", "/v1/restaurants/")
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["name"], "Dhanmondi")
        # pending vendors are invisible
        pending_owner = make_user("p@test.io", role="vendor")
        make_vendor_branch(pending_owner, status=Vendor.Status.PENDING)
        self._invalidate()
        self.assertEqual(len(api(None, "get", "/v1/restaurants/").json()), 1)
        # text search hits vendor name, branch name or cuisines
        self._invalidate()
        hits = api(None, "get", "/v1/restaurants/?q=kacchi").json()
        self.assertEqual(len(hits), 1)
        self.assertEqual(api(None, "get", "/v1/restaurants/?q=zzz").json(), [])

    def test_menu_tree_hides_unavailable(self):
        self._invalidate()
        data = api(None, "get", f"/v1/restaurants/{self.branch.uuid}/").json()
        self.assertEqual(data["menu"][0]["items"][0]["name"], "Kacchi Full")
        self.item.available = False
        self.item.save()
        self._invalidate()
        data = api(None, "get", f"/v1/restaurants/{self.branch.uuid}/").json()
        self.assertEqual(data["menu"][0]["items"], [])

    def test_distance_sorted_nearby(self):
        self._invalidate()
        rows = api(None, "get", "/v1/restaurants/?lat=23.79&lng=90.40").json()
        self.assertIn("distance_m", rows[0])
