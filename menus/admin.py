from django.contrib import admin

from .models import Category, Item, Option, OptionGroup


class OptionInline(admin.TabularInline):
    model = Option


class OptionGroupInline(admin.TabularInline):
    model = OptionGroup
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "position")
    list_filter = ("branch",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "base_price_minor", "available")
    list_filter = ("branch", "available")
    inlines = (OptionGroupInline,)


@admin.register(OptionGroup)
class OptionGroupAdmin(admin.ModelAdmin):
    list_display = ("title", "item", "min_select", "max_select")
    inlines = (OptionInline,)
