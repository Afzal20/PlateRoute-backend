from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import (DeviceRegistry, NotificationOutbox, NotificationPreference,
                     NotificationTemplate)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(ModelAdmin):
    list_display = ("code", "channel", "locale", "active")
    list_filter = ("channel", "locale", "active")
    search_fields = ("code", "subject", "body")


@admin.register(DeviceRegistry)
class DeviceRegistryAdmin(ModelAdmin):
    list_display = ("user", "platform", "app_version", "last_seen_at")
    list_filter = ("platform",)
    search_fields = ("user__email", "fcm_token")


@admin.register(NotificationOutbox)
class NotificationOutboxAdmin(ModelAdmin):
    """Backlog monitor: queued/failed rows are the pager signal (§12)."""

    list_display = ("channel", "recipient_user", "template", "state", "attempts",
                    "dedup_key", "scheduled_at", "sent_at")
    list_filter = ("channel", "state")
    search_fields = ("dedup_key", "recipient", "recipient_user__email")
    date_hierarchy = "created_at"
    readonly_fields = ("channel", "recipient_user", "recipient", "template", "context",
                       "dedup_key", "attempts", "scheduled_at", "sent_at", "created_at", "updated_at")

    # Delivery is the worker's job (send_notifications); admin is for
    # inspecting the backlog and diagnosing failed rows.
    def has_add_permission(self, request):
        return False


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    list_display = ("user", "kind", "email", "push", "sms")
    list_filter = ("kind", "email", "push", "sms")
    search_fields = ("user__email",)