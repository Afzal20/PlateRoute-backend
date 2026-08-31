from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import CourierDaily, DailyBranchMetrics


@admin.register(DailyBranchMetrics)
class DailyBranchMetricsAdmin(ModelAdmin):
    list_display = ("date", "branch", "orders_count", "gmv_minor", "completion_ratio")
    list_filter = ("date",)


@admin.register(CourierDaily)
class CourierDailyAdmin(ModelAdmin):
    list_display = ("courier", "date", "drops", "earnings_minor")