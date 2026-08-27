from rest_framework import serializers

from .models import Order, OrderEvent, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("id", "menu_item_ref", "title_snapshot", "qty", "unit_price_minor", "options", "line_total_minor")


class OrderEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderEvent
        fields = ("seq", "from_status", "to_status", "actor_type", "reason", "payload", "created_at")


class OrderSerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(slug_field="uuid", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("uuid", "status", "branch", "currency", "items_total_minor", "discount_minor",
                  "delivery_fee_minor", "vat_minor", "tip_minor", "grand_total_minor", "address",
                  "eta", "placed_at", "accepted_at", "delivered_at", "cancel_reason", "items")
