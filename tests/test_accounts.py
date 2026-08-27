from django.test import TestCase

from .helpers import api, make_user


class RoleOnboardTests(TestCase):
    def test_customer_can_become_courier_once(self):
        user = make_user()
        res = api(self.client, user, "post", "/auth/role/", {"role": "courier"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["role"], "courier")
        # second onboarding attempt is rejected
        res = api(self.client, user, "post", "/auth/role/", {"role": "vendor"})
        self.assertEqual(res.status_code, 409)

    def test_requires_auth(self):
        self.assertEqual(api(self.client, None, "post", "/auth/role/", {"role": "courier"}).status_code, 401)
