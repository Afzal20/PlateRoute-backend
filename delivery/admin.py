from django.contrib import admin

from .models import CourierProfile, DeliveryOffer, DeliveryTask, LocationPing


@admin.register(CourierProfile)
class CourierProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "vehicle", "plate", "is_online", "last_online_at")
    list_filter = ("vehicle", "is_online")
    search_fields = ("user__email", "plate", "license")
    readonly_fields = ("last_online_at",)


@admin.register(DeliveryTask)
class DeliveryTaskAdmin(admin.ModelAdmin):
    list_display = ("order", "state", "courier", "courier_fee_minor", "promised_eta_minutes", "created_at")
    list_filter = ("state", "courier__vehicle")
    search_fields = ("order__uuid", "courier__user__email")
    date_hierarchy = "created_at"
    readonly_fields = ("uuid", "order", "state", "courier", "pickup_lat", "pickup_lng", "dropoff_lat",
                       "dropoff_lng", "promised_eta_minutes", "courier_fee_minor",
                       "claimed_at", "picked_at", "dropped_at", "created_at", "updated_at")

    # Task state is driven by the dispatch engine and courier actions only;
    # manual edits would desync order events (§4 rule 5).
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DeliveryOffer)
class DeliveryOfferAdmin(admin.ModelAdmin):
    list_display = ("task", "courier", "state", "expires_at", "response_ms", "created_at")
    list_filter = ("state", "courier__vehicle")
    search_fields = ("task__order__uuid", "courier__user__email")
    readonly_fields = ("task", "courier", "expires_at", "state", "response_ms", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False


@admin.register(LocationPing)
class LocationPingAdmin(admin.ModelAdmin):
    """Retention-managed telemetry (NFR-13/16); inspect, never edit."""

    list_display = ("courier", "task", "lat", "lng", "speed_mps", "heading_deg", "recorded_at")
    list_filter = ("courier__vehicle",)
    search_fields = ("courier__user__email",)
    date_hierarchy = "recorded_at"
    readonly_fields = ("courier", "task", "lat", "lng", "speed_mps", "heading_deg", "recorded_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # pruned only by the dispatch_sweep retention job
