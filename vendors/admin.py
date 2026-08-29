from django.contrib import admin

from .models import Branch, BranchHours, Closure, Vendor, VendorStaff


class BranchHoursInline(admin.TabularInline):
    model = BranchHours
    extra = 0


class VendorStaffInline(admin.TabularInline):
    model = VendorStaff
    extra = 0


class BranchInline(admin.StackedInline):
    model = Branch
    extra = 0
    show_change_link = True


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """FR-CAT-02: superadmin approval workflow lives here."""

    list_display = ("name", "slug", "owner", "status", "commission_bp", "city_preview")
    list_filter = ("status",)
    search_fields = ("name", "slug", "legal_name", "owner__email")
    readonly_fields = ("slug",)
    actions = ("approve", "pause")
    inlines = (BranchInline,)

    @admin.display(description="Cities")
    def city_preview(self, obj):
        return ", ".join(dict.fromkeys(b.city for b in obj.branches.all())) or "-"

    @admin.action(description="Approve selected vendors")
    def approve(self, request, queryset):
        queryset.filter(status=Vendor.Status.PENDING).update(status=Vendor.Status.APPROVED)

    @admin.action(description="Pause selected vendors")
    def pause(self, request, queryset):
        queryset.filter(status=Vendor.Status.APPROVED).update(status=Vendor.Status.PAUSED)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "city", "phone", "is_accepting", "prep_minutes",
                    "min_order_minor", "avg_rating", "rating_count")
    list_filter = ("city", "is_accepting")
    search_fields = ("name", "vendor__name", "phone", "address_text")
    readonly_fields = ("uuid", "created_at", "updated_at", "avg_rating", "rating_count")
    inlines = (BranchHoursInline, VendorStaffInline)


@admin.register(Closure)
class ClosureAdmin(admin.ModelAdmin):
    list_display = ("branch", "starts_at", "ends_at", "reason")
    list_filter = ("branch",)
    search_fields = ("branch__name", "reason")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(VendorStaff)
class VendorStaffAdmin(admin.ModelAdmin):
    list_display = ("user", "branch", "role", "invited_by")
    list_filter = ("role", "branch")
    search_fields = ("user__email", "branch__name")
