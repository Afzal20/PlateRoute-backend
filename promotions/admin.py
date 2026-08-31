from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Coupon, Redemption


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ("code", "kind", "value", "branch", "starts_at", "ends_at",
                    "max_redemptions", "per_user_limit", "active")
    list_filter = ("kind", "active", "branch")
    search_fields = ("code",)

    def get_readonly_fields(self, request, obj=None):
        # codes are immutable once live so redemption history stays coherent
        return ("code",) if obj else ()


@admin.register(Redemption)
class RedemptionAdmin(ModelAdmin):
    """Financial record: read-only, like ledger rows."""

    list_display = ("coupon", "user", "order_id", "redeemed_at")
    list_filter = ("coupon__kind", "coupon")
    search_fields = ("coupon__code", "user__email")
    date_hierarchy = "redeemed_at"
    readonly_fields = ("coupon", "user", "order_id", "redeemed_at")

    def has_add_permission(self, request):
        return False  # redemptions are written only by checkout
