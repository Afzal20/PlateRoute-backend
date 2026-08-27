from django.contrib import admin

from .models import Coupon, Redemption


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "kind", "value", "ends_at", "active")
    list_filter = ("kind", "active")
    search_fields = ("code",)


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "user", "order_id", "redeemed_at")
