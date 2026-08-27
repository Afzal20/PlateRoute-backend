from django.contrib import admin

from .models import OutboxMessage, RuntimeConfig


@admin.register(RuntimeConfig)
class RuntimeConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "version")


@admin.register(OutboxMessage)
class OutboxMessageAdmin(admin.ModelAdmin):
    list_display = ("kind", "created_at", "processed_at")
    list_filter = ("kind",)
    readonly_fields = ("kind", "payload", "created_at", "updated_at", "processed_at")
