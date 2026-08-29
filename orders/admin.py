from django.contrib import admin

from .models import IdempotencyRecord, Order, OrderEvent, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("menu_item_ref", "title_snapshot", "qty", "unit_price_minor", "options", "line_total_minor")


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    ordering = ("seq",)
    readonly_fields = ("seq", "from_status", "to_status", "actor_type", "actor_id", "reason", "payload", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False  # events come only from the state machine


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "uuid", "customer", "branch", "status", "grand_total_minor",
                    "currency", "placed_at", "delivered_at")
    list_filter = ("status", "currency", "branch__city")
    search_fields = ("uuid", "customer__email", "branch__name", "branch__vendor__name")
    date_hierarchy = "placed_at"
    readonly_fields = ("uuid", "customer", "branch", "currency", "items_total_minor", "discount_minor",
                       "delivery_fee_minor", "vat_minor", "tip_minor", "grand_total_minor",
                       "address", "coupon", "eta", "placed_at", "accepted_at", "delivered_at")
    inlines = (OrderItemInline, OrderEventInline)

    # Money columns and identity are system-owned; support staff use the
    # backoffice/transition API so every mutation keeps its audit event.
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ("order", "seq", "from_status", "to_status", "actor_type", "actor_id", "reason", "created_at")
    list_filter = ("actor_type", "to_status")
    search_fields = ("order__uuid", "reason")
    date_hierarchy = "created_at"
    readonly_fields = ("order", "seq", "from_status", "to_status", "actor_type", "actor_id", "reason", "payload", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # append-only audit (§8.7)


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "endpoint", "status_code", "created_at")
    list_filter = ("endpoint",)
    search_fields = ("user__email", "key")
    readonly_fields = ("user", "key", "endpoint", "response", "status_code", "created_at", "updated_at")
