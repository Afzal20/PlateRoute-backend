from django.contrib import admin
from django.utils import timezone

from .models import Message, Participant, Report, Thread


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("uuid", "kind", "subject", "order", "message_count", "last_message_at", "closed_at")
    list_filter = ("kind", "closed_at")
    search_fields = ("subject", "order__uuid", "participants__user__email")
    date_hierarchy = "created_at"
    readonly_fields = ("uuid", "kind", "order", "created_by", "message_count",
                       "last_message_at", "created_at", "updated_at")
    inlines = (ParticipantInline,)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Moderation screen: hide/restore bodies, never rewrite history."""

    list_display = ("id", "thread", "sender", "kind", "short_body", "hidden_at", "created_at")
    list_filter = ("kind", "hidden_at", "thread__kind")
    search_fields = ("body", "sender__email", "thread__subject")
    date_hierarchy = "created_at"
    readonly_fields = ("thread", "sender", "kind", "body", "reply_to", "meta", "created_at")
    actions = ("hide", "restore")

    @admin.display(description="Body")
    def short_body(self, obj):
        return (obj.body or "")[:60]

    @admin.action(description="Hide selected messages (moderation)")
    def hide(self, request, queryset):
        queryset.filter(hidden_at__isnull=True).update(hidden_at=timezone.now())

    @admin.action(description="Restore selected messages")
    def restore(self, request, queryset):
        queryset.update(hidden_at=None)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("user", "thread", "role", "last_read_message_id", "left_at", "muted_until")
    list_filter = ("role", "thread__kind")
    search_fields = ("user__email", "thread__subject")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Operator queue for chat abuse reports (outcome + resolver audited)."""

    list_display = ("message", "reported_by", "reason", "outcome", "resolved_by", "created_at")
    list_filter = ("outcome",)
    search_fields = ("reason", "reported_by__email", "message__body")
    date_hierarchy = "created_at"
    readonly_fields = ("message", "reported_by", "reason", "created_at")