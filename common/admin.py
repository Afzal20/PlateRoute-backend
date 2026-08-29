from django.contrib import admin

from .models import OutboxMessage, RuntimeConfig


@admin.register(RuntimeConfig)
class RuntimeConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "version", "description")
    search_fields = ("key", "description")
    ordering = ("key",)
    readonly_fields = ("version",)  # bumps only through the backoffice bridge


@admin.register(OutboxMessage)
class OutboxMessageAdmin(admin.ModelAdmin):
    """Append-only audit of domain events; nothing is editable here."""

    list_display = ("kind", "created_at", "processed_at")
    list_filter = ("kind", "processed_at")
    date_hierarchy = "created_at"
    search_fields = ("payload",)
    readonly_fields = ("kind", "payload", "uuid", "created_at", "updated_at", "processed_at")

    def has_add_permission(self, request):
        return False  # events are emitted by services, never typed by hand
