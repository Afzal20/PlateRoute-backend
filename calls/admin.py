from django.contrib import admin

from .models import CallEvent, CallSession


class CallEventInline(admin.TabularInline):
    model = CallEvent
    extra = 0
    ordering = ("occurred_at",)
    readonly_fields = ("type", "payload", "source", "occurred_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False  # events are written by app actions and the LiveKit webhook


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    """§11 metadata-only calls: no audio exists to inspect, just lifecycle."""

    list_display = ("id", "room_name", "initiator", "callee", "status", "connected_at", "ended_at")
    list_filter = ("status",)
    search_fields = ("room_name", "initiator__email", "callee__email", "scope_object")
    date_hierarchy = "created_at"
    readonly_fields = ("uuid", "thread", "initiator", "callee", "status", "scope_object",
                       "connected_at", "ended_at", "end_reason", "room_name", "created_at", "updated_at")
    inlines = (CallEventInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # abuse metrics depend on the full session history


@admin.register(CallEvent)
class CallEventAdmin(admin.ModelAdmin):
    list_display = ("session", "type", "source", "occurred_at")
    list_filter = ("type", "source")
    search_fields = ("session__room_name",)
    date_hierarchy = "occurred_at"
    readonly_fields = ("session", "type", "payload", "source", "occurred_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False