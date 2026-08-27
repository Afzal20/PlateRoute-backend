from rest_framework.permissions import BasePermission


def role_required(*roles):
    """Permission class factory keyed on accounts.User.role (staff bypasses)."""

    class RolePermission(BasePermission):
        message = "Your role cannot perform this action."

        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and (user.role in roles or user.is_staff))

    return RolePermission
