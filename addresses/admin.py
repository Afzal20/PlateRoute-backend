from django.contrib import admin

from .models import Address, GeocodeCache


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "city", "is_default")
    search_fields = ("user__email", "city")


@admin.register(GeocodeCache)
class GeocodeCacheAdmin(admin.ModelAdmin):
    list_display = ("provider", "input_hash", "ttl_expires_at")
