from django.db import transaction
from rest_framework import serializers

from vendors.models import Branch

from .models import Category, Item, Option, OptionGroup


class CategorySerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(slug_field="uuid", queryset=Branch.objects.all(), write_only=True)

    class Meta:
        model = Category
        fields = ("uuid", "branch", "name", "position")

    def create(self, validated):
        return Category.objects.create(**validated)


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ("id", "label", "price_delta_minor", "is_default", "available")


class OptionGroupSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, required=False)

    class Meta:
        model = OptionGroup
        fields = ("id", "title", "min_select", "max_select", "options")


class ItemSerializer(serializers.ModelSerializer):
    groups = OptionGroupSerializer(many=True, required=False)
    category_name = serializers.CharField(source="category.name", read_only=True)
    branch = serializers.CharField(source="category.branch.uuid", read_only=True)
    category = serializers.SlugRelatedField(slug_field="uuid", queryset=Category.objects.all(), write_only=True)

    class Meta:
        model = Item
        fields = ("uuid", "category", "category_name", "branch", "name", "description", "image_url",
                  "base_price_minor", "currency", "available", "sort_key", "groups")

    @transaction.atomic
    def create(self, validated):
        groups = validated.pop("groups", [])
        item = super().create(validated)
        self._upsert_groups(item, groups)
        return item

    @transaction.atomic
    def update(self, instance, validated):
        groups = validated.pop("groups", None)
        item = super().update(instance, validated)
        if groups is not None:  # groups payload replaces the whole tree
            item.groups.all().delete()
            self._upsert_groups(item, groups)
        return item

    @staticmethod
    def _upsert_groups(item, groups):
        for entry in groups:
            options = entry.pop("options", [])
            group = OptionGroup.objects.create(item=item, **entry)
            Option.objects.bulk_create(Option(group=group, **o) for o in options)
