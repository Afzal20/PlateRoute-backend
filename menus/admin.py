from django.contrib import admin
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
    list_display = ("name", "branch", "base_price_minor", "currency", "available", "sort_key")
    list_filter = ("branch", "available", "currency")
    search_fields = ("name", "description", "branch__name", "branch__vendor__name")
    readonly_fields = ("uuid", "branch", "created_at", "updated_at")
    inlines = (OptionGroupInline,)


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
