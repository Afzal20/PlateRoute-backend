from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PasswordResetOTP, Profile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ("email", "role", "is_staff", "is_active", "date_joined", "deleted_at")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email",)
    ordering = ("email",)
    readonly_fields = ("date_joined", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("role", "deleted_at")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "is_active", "groups", "user_permissions")}),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {"fields": ("email", "password1", "password2")}),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "token_version")
    search_fields = ("user__email",)
    readonly_fields = ("token_version",)


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    """Sensitive: hashed codes are never editable, only inspectable."""

    list_display = ("user", "created_at", "expires_at", "used")
    list_filter = ("used",)
    search_fields = ("user__email",)
    readonly_fields = ("user", "code_hash", "created_at", "expires_at", "used")
