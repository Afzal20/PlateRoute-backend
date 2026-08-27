from django.contrib import admin

from .models import Invoice, LedgerEntry, Payment, Refund, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "gateway", "amount_minor", "state", "captured_at")
    list_filter = ("gateway", "state")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("payment", "amount_minor", "reason", "state")
    list_filter = ("state", "reason")


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_type", "order", "payee_type", "amount_minor", "batch_uuid")
    list_filter = ("entry_type",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("full_number", "order", "issued_at")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "event_id", "state", "retries", "received_at")
    list_filter = ("provider", "state")
