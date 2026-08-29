from django.contrib import admin

from .models import CourierDaily, DailyBranchMetrics


@admin.register(DailyBranchMetrics)
class DailyBranchMetricsAdmin(admin.ModelAdmin):
    list_display = ("date", "branch", "orders_count", "gmv_minor", "completion_ratio")
    list_filter = ("date",)


@admin.register(CourierDaily)
class CourierDailyAdmin(admin.ModelAdmin):
    list_display = ("courier", "date", "drops", "earnings_minor")