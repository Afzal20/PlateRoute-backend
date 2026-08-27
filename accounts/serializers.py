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
        fields = ("id", "email")


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
