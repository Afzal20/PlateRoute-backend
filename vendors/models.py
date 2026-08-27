from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel


class Vendor(models.Model):
    """Brand-level restaurant entity (§8.3); approval gates public visibility."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        PAUSED = "paused", "Paused"
        SUSPENDED = "suspended", "Suspended"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendors")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    legal_name = models.CharField(max_length=200, blank=True)
    trade_license_no = models.CharField(max_length=60, blank=True)
    cuisines = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    commission_bp = models.PositiveIntegerField(default=2000)

    def __str__(self):
        return self.name


class Branch(TimeStampedModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=120)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    address_text = models.CharField(max_length=255)
    city = models.CharField(max_length=80)
    phone = models.CharField(max_length=20, blank=True)
    prep_minutes = models.PositiveSmallIntegerField(default=20)
    min_order_minor = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="BDT")
    open_hours = models.JSONField(default=dict, blank=True)  # {"0": [["09:00","23:00"]]}
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    is_accepting = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.vendor.name} · {self.name}"

    @property
    def point(self):
        return (float(self.lat), float(self.lng))

    @property
    def open_now(self):
        windows = (self.open_hours or {}).get(str(timezone.localtime().weekday()))
        if not windows:
            return False
        now = timezone.localtime().time()
        return any(time.fromisoformat(a) <= now <= time.fromisoformat(b) for a, b in windows)

    def is_managed_by(self, user):
        return self.vendor.owner_id == user.id or self.staff.filter(user=user).exists()


class BranchHours(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="hours")
    weekday = models.PositiveSmallIntegerField()  # 0=Monday
    opens = models.TimeField()
    closes = models.TimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["branch", "weekday", "opens"], name="unique_branch_window")]


class Closure(TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="closures")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)


class VendorStaff(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        STAFF = "staff", "Staff"

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="staff")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="branch_memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["branch", "user"], name="unique_branch_staff")]
