from django.db import models


class DailyBranchMetrics(models.Model):
    """FR-REP-01/03: nightly aggregate so dashboards read cheap rows."""

    date = models.DateField()
    branch = models.ForeignKey("vendors.Branch", on_delete=models.CASCADE, related_name="daily_metrics")
    orders_count = models.PositiveIntegerField(default=0)
    gmv_minor = models.BigIntegerField(default=0)
    aov_minor = models.BigIntegerField(default=0)
    completion_ratio = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    cancels_by_reason = models.JSONField(default=dict, blank=True)
    avg_accept_secs = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["date", "branch"], name="unique_daily_branch")]


class CourierDaily(models.Model):
    courier = models.ForeignKey("delivery.CourierProfile", on_delete=models.CASCADE, related_name="daily_stats")
    date = models.DateField()
    drops = models.PositiveIntegerField(default=0)
    earnings_minor = models.BigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["courier", "date"], name="unique_courier_day")]