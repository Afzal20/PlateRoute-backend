from django.contrib import admin

from .models import IdempotencyRecord, Order, OrderEvent, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "branch", "status", "grand_total_minor", "placed_at")
    list_filter = ("status",)
    search_fields = ("customer__email", "branch__name")
    inlines = (OrderItemInline,)
    readonly_fields = ("placed_at", "accepted_at", "delivered_at")


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ("order", "seq", "from_status", "to_status", "actor_type", "created_at")
    list_filter = ("actor_type", "to_status")
    readonly_fields = ("order", "seq", "from_status", "to_status", "actor_type", "actor_id", "reason", "payload", "created_at")


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "endpoint", "status_code", "created_at")
    readonly_fields = ("user", "key", "endpoint", "response", "status_code")
