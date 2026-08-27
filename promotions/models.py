from django.conf import settings
from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    """FR-CART-04: percent / fixed / free-delivery vouchers."""

    class Kind(models.TextChoices):
        PERCENT = "percent", "Percent"
        FIXED = "fixed", "Fixed"
        FREE_DELIVERY = "free_delivery", "Free delivery"

    code = models.CharField(max_length=30, unique=True)
    kind = models.CharField(max_length=15, choices=Kind.choices)
    value = models.PositiveIntegerField()  # basis points for percent, minor units for fixed
    branch = models.ForeignKey("vendors.Branch", null=True, blank=True, on_delete=models.CASCADE, related_name="coupons")
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()
    max_redemptions = models.PositiveIntegerField(default=0)  # 0 = unlimited
    per_user_limit = models.PositiveSmallIntegerField(default=1)
    min_basket_minor = models.BigIntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class Redemption(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coupon_redemptions")
    # orders.Order pk; plain integer ref avoids a forward dependency (orders binds it at placement)
    order_id = models.BigIntegerField(null=True, blank=True)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["coupon", "user", "order_id"], name="unique_redemption")]
