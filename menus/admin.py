from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import Category, Item, Option, OptionGroup


class OptionInline(TabularInline):
    model = Option
    extra = 0


class OptionGroupInline(TabularInline):
    model = OptionGroup
    extra = 0
    show_change_link = True


class ItemInline(TabularInline):
    model = Item
    extra = 0
    show_change_link = True
    fields = ("image_preview", "name", "base_price_minor", "currency", "available")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        url = obj.image_url or obj.local_image_url
        if url:
            return format_html('<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px;" />', url)
        return "-"
    image_preview.short_description = "Image"


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "branch", "position", "created_at")
    list_filter = ("branch",)
    search_fields = ("name", "branch__name", "branch__vendor__name")
    ordering = ("branch", "position")
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = (ItemInline,)


@admin.register(Item)
class ItemAdmin(ModelAdmin):
    list_display = ("image_preview", "name", "category", "branch", "base_price_minor", "currency", "available", "sort_key")
    list_filter = ("branch", "available", "currency", "category")
    search_fields = ("name", "description", "branch__name", "branch__vendor__name")
    readonly_fields = ("uuid", "branch", "image_preview", "created_at", "updated_at")
    inlines = (OptionGroupInline,)

    def image_preview(self, obj):
        url = obj.image_url or obj.local_image_url
        if url:
            return format_html('<img src="{}" style="width: 48px; height: 48px; object-fit: cover; border-radius: 8px;" />', url)
        return "-"
    image_preview.short_description = "Image"


@admin.register(OptionGroup)
class OptionGroupAdmin(ModelAdmin):
    list_display = ("title", "item", "min_select", "max_select")
    list_filter = ("item__branch",)
    search_fields = ("title", "item__name")
    inlines = (OptionInline,)


@admin.register(Option)
class OptionAdmin(ModelAdmin):
    list_display = ("label", "group", "price_delta_minor", "is_default", "available")
    list_filter = ("available", "is_default", "group__item__branch")
    search_fields = ("label", "group__title", "item__name")
