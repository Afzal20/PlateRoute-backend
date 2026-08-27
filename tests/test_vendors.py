from django.test import TestCase

from vendors.models import Branch, Vendor
from .helpers import api, make_user


def make_vendor_branch(owner, status=Vendor.Status.APPROVED):
    vendor = Vendor.objects.create(owner=owner, name="Kacchi Bhai", slug=f"kacchi-{owner.id}", status=status)
    branch = Branch.objects.create(
        vendor=vendor, name="Dhanmondi", lat=23.8, lng=90.4, address_text="RD 5", city="Dhaka",
        open_hours={"0": [["09:00", "23:00"]]},
    )
    return vendor, branch


class VendorTests(TestCase):
    def setUp(self):
        self.vendor_user = make_user("v@test.io", role="vendor")
        self.customer = make_user("c@test.io")

    def test_vendor_role_required_to_create(self):
        payload = {"name": "Sultan's Dine"}
        self.assertEqual(api(self.customer, "post", "/v1/vendors/", payload).status_code, 403)
        res = api(self.vendor_user, "post", "/v1/vendors/", payload)
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["slug"])

    def test_submit_and_owner_scoping(self):
        vendor, _ = make_vendor_branch(self.vendor_user, status=Vendor.Status.DRAFT)
        res = api(self.vendor_user, "post", f"/v1/vendors/{vendor.slug}/submit/")
        self.assertEqual(res.json()["status"], "pending")
        other = make_user("v2@test.io", role="vendor")
        self.assertEqual(api(other, "post", f"/v1/vendors/{vendor.slug}/submit/").status_code, 404)

    def test_branch_crud_hours_and_staff(self):
        vendor, branch = make_vendor_branch(self.vendor_user)
        # staff member can manage the branch
        staff_user = make_user("s@test.io", role="vendor")
        res = api(self.vendor_user, "post", f"/v1/branches/{branch.uuid}/team/", {"user": staff_user.id, "role": "manager"})
        self.assertEqual(res.status_code, 201)
        res = api(staff_user, "patch", f"/v1/branches/{branch.uuid}/", {"prep_minutes": 30})
        self.assertEqual(res.json()["prep_minutes"], 30)
        # bulk replace hours
        res = api(self.vendor_user, "post", f"/v1/branches/{branch.uuid}/hours/", {"hours": [{"weekday": 0, "opens": "09:00", "closes": "17:00"}]})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(branch.hours.count(), 1)
        # customers see nothing here (owner scope)
        self.assertEqual(api(self.customer, "get", "/v1/branches/").status_code, 200)
