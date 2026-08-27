from django.contrib import admin

from .models import Branch, BranchHours, Closure, Vendor, VendorStaff


class BranchHoursInline(admin.TabularInline):
    model = BranchHours


class VendorStaffInline(admin.TabularInline):
    model = VendorStaff


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "commission_bp")
    list_filter = ("status",)
    search_fields = ("name", "owner__email")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "city", "is_accepting", "avg_rating")
    list_filter = ("city", "is_accepting")
    inlines = (BranchHoursInline, VendorStaffInline)


@admin.register(Closure)
class ClosureAdmin(admin.ModelAdmin):
    list_display = ("branch", "starts_at", "ends_at", "reason")
