"""FR-REP-03: aggregate builders + reporting endpoints' query layer."""
from datetime import timedelta

from django.db.models import Avg, Count, F, Sum
from django.utils import timezone

from .models import DailyBranchMetrics


def rebuild_daily(days=1):
    """Recompute yesterday's per-branch metrics (idempotent upsert)."""
    from orders.models import Order

    day = (timezone.now() - timedelta(days=days)).date()
    built = 0
    for row in (Order.objects.filter(placed_at__date=day).values("branch")
                .annotate(total=Count("id"), gmv=Sum("grand_total_minor"))):
        branch_id = row["branch"]
        done = Order.objects.filter(branch_id=branch_id, placed_at__date=day, status="delivered").count()
        DailyBranchMetrics.objects.update_or_create(
            date=day, branch_id=branch_id,
            defaults=dict(orders_count=row["total"], gmv_minor=row["gmv"] or 0,
                          aov_minor=(row["gmv"] or 0) // max(row["total"], 1),
                          completion_ratio=round(done / max(row["total"], 1), 4)))
        built += 1
    return built


def branch_summary(branch, days=30):
    """FR-REP-02: cheap reads straight off the summary table."""
    since = (timezone.now() - timedelta(days=days)).date()
    rows = DailyBranchMetrics.objects.filter(branch=branch, date__gte=since)
    agg = rows.aggregate(total_orders=Sum("orders_count"), gmv=Sum("gmv_minor"))
    return {"days": days, "orders": agg["total_orders"] or 0, "gmv_minor": agg["gmv"] or 0,
            "series": [{"date": r.date, "orders": r.orders_count, "gmv_minor": r.gmv_minor,
                        "completion_ratio": float(r.completion_ratio)} for r in rows.order_by("date")]}