from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Ticket, TicketMessage


class TicketMessageInline(TabularInline):
    model = TicketMessage
    extra = 0


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = ("uuid", "subject", "opened_by", "category", "priority", "status", "sla_due_at")
    list_filter = ("status", "priority", "category")
    inlines = (TicketMessageInline,)