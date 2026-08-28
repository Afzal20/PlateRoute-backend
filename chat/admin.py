from django.contrib import admin

from .models import Message, Participant, Report, Thread


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("kind", "order", "subject", "message_count", "last_message_at", "closed_at")
    list_filter = ("kind",)


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender", "kind", "body", "created_at", "hidden_at")
    list_filter = ("kind",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("message", "reported_by", "reason", "outcome", "created_at")