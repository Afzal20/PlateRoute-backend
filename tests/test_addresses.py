from django.test import TestCase

from addresses.models import Address
from .helpers import api, make_user


def make_address(user, i=0, **kw):
    defaults = dict(label=f"Home{i}", receiver_name="A", phone="01700", lat=23.8, lng=90.4, city="Dhaka")
    defaults.update(kw)
    return Address.objects.create(user=user, **defaults)


class AddressTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_first_address_becomes_default_and_unique(self):
        make_address(self.user)  # auto-default
        make_address(self.user, 1, is_default=True)  # steals the default
        self.assertEqual(self.user.addresses.filter(is_default=True).count(), 1)

    def test_limit_20(self):
        for i in range(20):
            make_address(self.user, i)
        res = api(self.user, "post", "/v1/addresses/", {"label": "x", "receiver_name": "A", "phone": "017", "lat": 1, "lng": 1, "city": "Dhaka"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "address.limit")

    def test_scoping_and_default_action(self):
        other = make_user("b@test.io")
        mine = make_address(self.user)
        theirs = make_address(other)
        self.assertNotIn(theirs.pk, self.user.addresses.values_list("pk", flat=True))
        res = api(self.user, "post", f"/v1/addresses/{mine.uuid}/default/")
        self.assertEqual(res.status_code, 200)

    def test_geocode_cache(self):
        api(self.user, "get", "/v1/geocode/?q=dhanmondi")
        res = api(self.user, "get", "/v1/geocode/?q=dhanmondi")
        self.assertEqual(res.status_code, 200)
