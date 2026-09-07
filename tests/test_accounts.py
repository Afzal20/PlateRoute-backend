from django.test import TestCase

from .helpers import api, make_user


class RoleOnboardTests(TestCase):
    def test_customer_can_become_courier_once(self):
        user = make_user()
        res = api(user, "post", "/auth/role/", {"role": "courier"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["role"], "courier")
        # second onboarding attempt is rejected
        self.assertEqual(api(user, "post", "/auth/role/", {"role": "vendor"}).status_code, 409)

    def test_requires_auth(self):
        self.assertEqual(api(None, "post", "/auth/role/", {"role": "courier"}).status_code, 401)


class GoogleLoginTests(TestCase):
    def test_invalid_token_rejected(self):
        res = api(None, "post", "/auth/google/login/", {"id_token": "bogus"})
        self.assertEqual(res.status_code, 401)

    def test_missing_token_rejected(self):
        res = api(None, "post", "/auth/google/login/", {})
        self.assertEqual(res.status_code, 400)

    def test_valid_token_mints_jwt(self):
        from unittest.mock import patch
        from django.contrib.auth import get_user_model
        with patch("google.oauth2.id_token.verify_oauth2_token",
                   return_value={"email": "g@test.io", "email_verified": True}):
            res = api(None, "post", "/auth/google/login/", {"id_token": "good"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.json())
        self.assertTrue(get_user_model().objects.filter(email="g@test.io").exists())

    def test_unverified_email_rejected(self):
        from unittest.mock import patch
        with patch("google.oauth2.id_token.verify_oauth2_token",
                   return_value={"email": "g2@test.io", "email_verified": False}):
            res = api(None, "post", "/auth/google/login/", {"id_token": "good"})
        self.assertEqual(res.status_code, 403)
