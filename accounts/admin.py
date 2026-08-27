from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PasswordResetOTP, User, Profile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ("email", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email",)
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "is_active", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"fields": ("email", "password1", "password2")}),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "token_version")


@admin.register(PasswordResetOTP)
class PasswordResetOTPTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "used")
    list_filter = ("used",)
    search_fields = ("user__email",)
    readonly_fields = ("user", "code_hash", "created_at", "expires_at", "used")
