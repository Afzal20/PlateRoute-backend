from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Address, GeocodeCache


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = ("label", "user", "receiver_name", "phone", "city", "is_default", "created_at")
    list_filter = ("city", "is_default")
    search_fields = ("user__email", "receiver_name", "phone", "street", "area")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(GeocodeCache)
class GeocodeCacheAdmin(ModelAdmin):
    list_display = ("provider", "input_hash", "fetched_at", "ttl_expires_at")
    list_filter = ("provider",)
    search_fields = ("input_hash",)
    readonly_fields = ("provider", "input_hash", "result", "fetched_at")
