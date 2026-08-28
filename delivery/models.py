from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class CourierProfile(models.Model):
    class Vehicle(models.TextChoices):
        BIKE = "bike", "Bike"
        BICYCLE = "bicycle", "Bicycle"
        CAR = "car", "Car"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courier_profile")
    vehicle = models.CharField(max_length=8, choices=Vehicle.choices, default=Vehicle.BIKE)
    plate = models.CharField(max_length=20, blank=True)
    license = models.CharField(max_length=40, blank=True)
    is_online = models.BooleanField(default=False)
    last_online_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} ({self.vehicle})"


class DeliveryTask(TimeStampedModel):
    """§8.8: one task per order, created when the order becomes ready."""

    class State(models.TextChoices):
        CREATED = "created", "Created"
        OFFERING = "offering", "Offering"
        CLAIMED = "claimed", "Claimed"
        AT_VENDOR = "at_vendor", "At vendor"
        PICKED = "picked", "Picked up"
        ARRIVED = "arrived", "Arrived at dropoff"
        DROPPED = "dropped", "Dropped"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED_NO_COURIER = "expired_no_courier", "No courier accepted"

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="delivery_task")
    state = models.CharField(max_length=20, choices=State.choices, default=State.CREATED, db_index=True)
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lat = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lng = models.DecimalField(max_digits=9, decimal_places=6)
    promised_eta_minutes = models.PositiveSmallIntegerField(default=45)
    courier_fee_minor = models.BigIntegerField(default=0)
    courier = models.ForeignKey(CourierProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    claimed_at = models.DateTimeField(null=True, blank=True)
    picked_at = models.DateTimeField(null=True, blank=True)
    dropped_at = models.DateTimeField(null=True, blank=True)


class DeliveryOffer(TimeStampedModel):
    class State(models.TextChoices):
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"

    task = models.ForeignKey(DeliveryTask, on_delete=models.CASCADE, related_name="offers")
    courier = models.ForeignKey(CourierProfile, on_delete=models.CASCADE, related_name="offers")
    expires_at = models.DateTimeField()
    state = models.CharField(max_length=10, choices=State.choices, default=State.SENT)
    response_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["task", "courier"], name="unique_task_offer")]


class LocationPing(models.Model):
    """FR-DLV-04: batched telemetry, pruned after 30 days (NFR-13)."""

    courier = models.ForeignKey(CourierProfile, on_delete=models.CASCADE, related_name="pings")
    task = models.ForeignKey(DeliveryTask, null=True, blank=True, on_delete=models.SET_NULL, related_name="pings")
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    speed_mps = models.PositiveSmallIntegerField(null=True, blank=True)
    heading_deg = models.PositiveSmallIntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True)
