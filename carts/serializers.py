from menus.models import Item
from rest_framework import serializers

from .models import CartItem


class CartItemSerializer(serializers.ModelSerializer):
    item = serializers.SlugRelatedField(slug_field="uuid", queryset=Item.objects.all())

    class Meta:
        model = CartItem
        fields = ("id", "item", "qty", "selected_options", "title_snapshot",
                  "unit_price_snapshot_minor", "line_total_minor")
        read_only_fields = ("title_snapshot", "unit_price_snapshot_minor", "line_total_minor")
