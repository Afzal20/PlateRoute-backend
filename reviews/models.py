from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    """FR-RVW-01/03: one review per completed order, plus optional courier stars."""

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="review")
    restaurant_stars = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    courier_stars = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    body = models.CharField(max_length=1000, blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .services import refresh_rating
        refresh_rating(self.order.branch_id)


class ReviewReply(models.Model):
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="reply")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_replies")
    body = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)