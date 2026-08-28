from django.contrib import admin

from .models import CourierProfile, DeliveryOffer, DeliveryTask, LocationPing


@admin.register(CourierProfile)
class CourierProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "vehicle", "is_online", "last_online_at")
    list_filter = ("vehicle", "is_online")


@admin.register(DeliveryTask)
class DeliveryTaskAdmin(admin.ModelAdmin):
    list_display = ("order", "state", "courier", "courier_fee_minor")
    list_filter = ("state",)


@admin.register(DeliveryOffer)
class DeliveryOfferAdmin(admin.ModelAdmin):
    list_display = ("task", "courier", "state", "expires_at")
    list_filter = ("state",)


@admin.register(LocationPing)
class LocationPingAdmin(admin.ModelAdmin):
    list_display = ("courier", "task", "recorded_at")
