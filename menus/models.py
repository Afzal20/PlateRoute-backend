from django.core.validators import MinValueValidator
from django.db import models

from common.models import TimeStampedModel


class Category(TimeStampedModel):
    branch = models.ForeignKey("vendors.Branch", on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=120)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["branch", "name"], name="unique_category_per_branch")]
        ordering = ("position", "id")

    def __str__(self):
        return self.name


class Item(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    branch = models.ForeignKey("vendors.Branch", on_delete=models.CASCADE, related_name="menu_items")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    base_price_minor = models.BigIntegerField(validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default="BDT")
    available = models.BooleanField(default=True)
    sort_key = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_key", "id")

    def save(self, *args, **kwargs):
        self.branch = self.category.branch  # denormalized for fast filters (§8.4)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class OptionGroup(TimeStampedModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="groups")
    title = models.CharField(max_length=120)
    min_select = models.PositiveSmallIntegerField(default=0)
    max_select = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(min_select__lte=models.F("max_select")), name="group_select_range"),
        ]


class Option(TimeStampedModel):
    group = models.ForeignKey(OptionGroup, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=120)
    price_delta_minor = models.BigIntegerField(default=0, validators=[MinValueValidator(0)])
    is_default = models.BooleanField(default=False)
    available = models.BooleanField(default=True)

    class Meta:
        ordering = ("id",)
