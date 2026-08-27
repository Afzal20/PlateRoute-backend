from django.conf import settings
from django.db import models

from common.models import TimeStampedModel

MAX_ADDRESSES = 20  # FR-AUTH-08


class Address(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=50)
    receiver_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    plus_code = models.CharField(max_length=40, blank=True)
    street = models.CharField(max_length=255, blank=True)
    area = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=80)
    postcode = models.CharField(max_length=12, blank=True)
    directions = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user"], condition=models.Q(is_default=True), name="unique_default_address"),
        ]
        ordering = ("-is_default", "id")

    def save(self, *args, **kwargs):
        if self.is_default:  # keep exactly one default per user
            self.user.addresses.exclude(pk=self.pk).update(is_default=False)
        elif not self.user.addresses.exclude(pk=self.pk).filter(is_default=True).exists():
            self.is_default = True  # first address becomes the default
        super().save(*args, **kwargs)

    @property
    def point(self):
        return (float(self.lat), float(self.lng))


class GeocodeCache(models.Model):
    """Provider-agnostic geocode cache keyed by normalized input (§9)."""

    provider = models.CharField(max_length=10)
    input_hash = models.CharField(max_length=64)
    result = models.JSONField(default=dict, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)
    ttl_expires_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["provider", "input_hash"], name="unique_geocode_input")]
