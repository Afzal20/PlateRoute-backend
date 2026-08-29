from django.contrib import admin

from .models import Ticket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("uuid", "subject", "opened_by", "category", "priority", "status", "sla_due_at")
    list_filter = ("status", "priority", "category")
    inlines = (TicketMessageInline,)