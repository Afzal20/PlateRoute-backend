from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from common.models import TimeStampedModel


class Cart(TimeStampedModel):
    """FR-CART-01: one server-side cart per customer, scoped to a branch."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    branch = models.ForeignKey("vendors.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    def clear(self):
        self.items.all().delete()
        self.branch = None
        self.save(update_fields=["branch"])


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey("menus.Item", on_delete=models.CASCADE, related_name="cart_items")
    qty = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    selected_options = models.JSONField(default=list, blank=True)  # [{group_id, option_id, label, price_delta_minor}]
    unit_price_snapshot_minor = models.BigIntegerField(default=0)
    title_snapshot = models.CharField(max_length=150)
    line_total_minor = models.BigIntegerField(default=0)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(qty__gte=1, qty__lte=50), name="cart_qty_range")]

    def save(self, *args, **kwargs):
        self.title_snapshot = self.item.name
        self.unit_price_snapshot_minor = self.item.base_price_minor
        self.line_total_minor = (self.unit_price_snapshot_minor + sum(
            o["price_delta_minor"] for o in self.selected_options)) * self.qty
        super().save(*args, **kwargs)

