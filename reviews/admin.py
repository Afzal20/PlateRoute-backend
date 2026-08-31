from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Review, ReviewReply


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("order", "restaurant_stars", "courier_stars", "hidden_at", "created_at")
    list_filter = ("restaurant_stars", "hidden_at")


@admin.register(ReviewReply)
class ReviewReplyAdmin(ModelAdmin):
    list_display = ("review", "author", "created_at")