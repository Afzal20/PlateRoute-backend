"""FR-RVW-03: rating aggregates maintained on the branch via tasks, not reads."""


def refresh_rating(branch_id):
    from django.db.models import Avg, Count

    from reviews.models import Review

    stats = Review.objects.filter(order__branch_id=branch_id, hidden_at__isnull=True) \
        .aggregate(avg=Avg("restaurant_stars"), count=Count("id"))
    from vendors.models import Branch
    Branch.objects.filter(pk=branch_id).update(
        avg_rating=stats["avg"] or 0, rating_count=stats["count"])