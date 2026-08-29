from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile, User
from .otp import OTP_LENGTH

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password")

    def create(self, validated):
        return User.objects.create_user(**validated)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "role")
        read_only_fields = ("role",)  # role changes ONLY via the /role/ onboarding endpoint — never a direct write


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """FR-AUTH-05: changing the account email requires the current password.

    On success other sessions are logged out (token_version bump) so a leaked
    session cannot silently rebind the account to an attacker's mailbox.
    """

    current_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ("id", "email", "role", "current_password")
        read_only_fields = ("role",)

    def validate(self, attrs):
        user = self.instance
        if "email" in attrs and attrs["email"] != user.email:
            password = attrs.pop("current_password", None)
            if not password or not user.check_password(password):
                raise serializers.ValidationError(
                    {"current_password": "Current password is required to change the email."})
        else:
            attrs.pop("current_password", None)
        return attrs

    def update(self, instance, validated_data):
        email_changed = "email" in validated_data and validated_data["email"] != instance.email
        instance = super().update(instance, validated_data)
        if email_changed:
            profile, _ = Profile.objects.get_or_create(user=instance)
            profile.bump_token_version()  # invalidate every other session (FR-AUTH-05)
        return instance


class RoleOnboardSerializer(serializers.Serializer):
    """FR-AUTH-07: attach a vendor or courier role to the current user."""

    role = serializers.ChoiceField(choices=["vendor", "courier"])


class TokenObtainSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"]
        password = attrs["password"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "Invalid credentials."})

        if not user.check_password(password):
            raise serializers.ValidationError({"email": "Invalid credentials."})

        if not user.is_active:
            raise serializers.ValidationError({"email": "Account disabled."})

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.bump_token_version()

        refresh = RefreshToken.for_user(user)
        refresh["token_version"] = profile.token_version

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        }


class PasswordResetOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetOTPConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # Exactly OTP_LENGTH characters, matching the code format that is emailed.
    otp = serializers.CharField(min_length=OTP_LENGTH, max_length=OTP_LENGTH)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
