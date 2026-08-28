from django.contrib import admin

from .models import CallEvent, CallSession


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "initiator", "callee", "status", "connected_at", "ended_at", "room_name")
    list_filter = ("status",)


@admin.register(CallEvent)
class CallEventAdmin(admin.ModelAdmin):
    list_display = ("session", "type", "source", "occurred_at")
    list_filter = ("type", "source")