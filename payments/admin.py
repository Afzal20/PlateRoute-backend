from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Invoice, LedgerEntry, Payment, Refund, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ("order", "gateway", "amount_minor", "currency", "state", "brand_last4", "captured_at")
    list_filter = ("gateway", "state", "currency")
    search_fields = ("order__uuid", "gateway_reference", "order__customer__email")
    date_hierarchy = "captured_at"
    readonly_fields = ("order", "gateway", "gateway_reference", "amount_minor", "currency",
                       "state", "brand_last4", "captured_at")

    # State moves only through the worker/capture service so ledger pairing
    # always matches the payment row (FR-PAY-03 discipline).
    def has_add_permission(self, request):
        return False


@admin.register(Refund)
class RefundAdmin(ModelAdmin):
    list_display = ("payment", "amount_minor", "reason", "state", "requested_by", "approved_by", "processed_at")
    list_filter = ("state", "reason")
    search_fields = ("payment__order__uuid", "requested_by__email")
    readonly_fields = ("payment", "amount_minor", "reason", "state", "requested_by", "approved_by", "processed_at")

    def has_add_permission(self, request):
        return False  # approval runs through the backoffice queue (FR-PAY-05)


@admin.register(LedgerEntry)
class LedgerEntryAdmin(ModelAdmin):
    """FR-ADM-04: the money record — strictly inspect-only."""

    list_display = ("entry_type", "order", "payee_type", "payee_id", "amount_minor", "currency", "batch_uuid", "created_at")
    list_filter = ("entry_type", "payee_type", "currency")
    search_fields = ("order__uuid", "batch_uuid")
    date_hierarchy = "created_at"
    readonly_fields = ("entry_type", "order", "payee_type", "payee_id", "amount_minor", "currency", "batch_uuid", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # double-entry rows must never disappear


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ("full_number", "order", "series", "number", "issued_at")
    search_fields = ("full_number", "order__uuid", "order__customer__email")
    readonly_fields = ("order", "series", "number", "full_number", "issued_at")

    def has_add_permission(self, request):
        return False  # numbering is serialized by the capture service (FR-PAY-07)


@admin.register(WebhookEvent)
class WebhookEventAdmin(ModelAdmin):
    """Dead-letter inspection for FR-PAY-03 retries."""

    list_display = ("provider", "event_id", "state", "retries", "received_at")
    list_filter = ("provider", "state")
    search_fields = ("event_id",)
    date_hierarchy = "received_at"
    readonly_fields = ("provider", "event_id", "payload", "state", "retries", "received_at")
