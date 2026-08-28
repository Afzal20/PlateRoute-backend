from django.contrib import admin

from .models import DeviceRegistry, NotificationOutbox, NotificationPreference, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "channel", "locale", "active")
    list_filter = ("channel", "active")


@admin.register(DeviceRegistry)
class DeviceRegistryAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "app_version", "last_seen_at")


@admin.register(NotificationOutbox)
class NotificationOutboxAdmin(admin.ModelAdmin):
    list_display = ("channel", "recipient_user", "template", "state", "attempts", "scheduled_at")
    list_filter = ("channel", "state")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "email", "push", "sms")
    list_filter = ("kind",)