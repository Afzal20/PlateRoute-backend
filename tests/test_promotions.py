from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from promotions.models import Coupon, Redemption
from .helpers import api, make_user
from .test_vendors import make_vendor_branch


def make_coupon(code="SAVE10", kind="percent", value=1000, **kw):
    defaults = dict(kind=kind, value=value, ends_at=timezone.now() + timedelta(days=1))
    defaults.update(kw)
    return Coupon.objects.create(code=code, **defaults)


class CouponTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.branch = make_vendor_branch(make_user("v@test.io", role="vendor"))[1]
        make_coupon()  # default SAVE10, 10%

    def _validate(self, code="SAVE10", subtotal=50000, **kw):
        return api(self.user, "post", "/v1/coupons/validate/", {"code": code, "subtotal_minor": subtotal, **kw})

    def test_kinds_math(self):
        self.assertEqual(self._validate(value=1000).json()["discount_minor"], 5000)  # 10% of 500
        fixed = make_coupon("F50", "fixed", 5000)
        res = self._validate("F50")
        self.assertEqual(res.json()["discount_minor"], 5000)
        free = make_coupon("FREESHIP", "free_delivery", 0)
        self.assertTrue(self._validate("FREESHIP").json()["free_delivery"])
        # fixed never exceeds the basket
        self.assertEqual(self._validate("F50", subtotal=1000).json()["discount_minor"], 1000)

    def test_rules(self):
        make_coupon("OLD", ends_at=timezone.now() - timedelta(days=1))
        self.assertEqual(self._validate("OLD").status_code, 400)
        make_coupon("MIN", "fixed", 1000, min_basket_minor=100000)
        self.assertEqual(self._validate("MIN").json()["code"], "coupon.min_basket")
        # per-user limit counts prior redemptions (created at checkout)
        limited = make_coupon("ONCE", per_user_limit=1)
        Redemption.objects.create(coupon=limited, user=self.user)
        res = self._validate("ONCE")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "coupon.per_user")

    def test_case_insensitive_lookup(self):
        res = self._validate("save10")
        self.assertEqual(res.status_code, 200)
