from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("title_snapshot", "unit_price_snapshot_minor", "line_total_minor", "selected_options")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "branch", "items_total", "updated_at")
    search_fields = ("user__email", "branch__name")
    list_filter = ("branch",)
    readonly_fields = ("user", "branch", "uuid", "created_at", "updated_at")
    inlines = (CartItemInline,)

    @admin.display(description="Basket (minor)")
    def items_total(self, obj):
        return sum(line.line_total_minor for line in obj.items.all())

    def has_add_permission(self, request):
        return False  # carts are created implicitly per user


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Inspect-only: snapshots are frozen by the pricing service."""

    list_display = ("cart", "title_snapshot", "qty", "unit_price_snapshot_minor", "line_total_minor")
    search_fields = ("title_snapshot", "cart__user__email")
    list_filter = ("cart__branch",)
    readonly_fields = ("cart", "item", "qty", "selected_options", "title_snapshot",
                       "unit_price_snapshot_minor", "line_total_minor")

    def has_add_permission(self, request):
        return False
