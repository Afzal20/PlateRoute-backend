import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect
from django.template.loader import render_to_string
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response

from .models import PasswordResetOTP, Profile, User
from .otp import hash_otp
from .serializers import RegisterSerializer, UserSerializer, TokenObtainSerializer, RoleOnboardSerializer
from .serializers import PasswordResetOTPConfirmSerializer, PasswordResetOTPRequestSerializer
from .throttles import (
    LoginThrottle,
    PasswordResetConfirmThrottle,
    PasswordResetRequestThrottle,
    RegisterThrottle,
)

logger = logging.getLogger(__name__)

GENERIC_RESET_MESSAGE = (
    "If the email exists, an OTP valid for "
    f"{PasswordResetOTP.TTL_MINUTES} minutes has been sent."
)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (RegisterThrottle,)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class RoleOnboardView(generics.GenericAPIView):
    """FR-AUTH-07: lets a customer become a vendor or courier."""

    serializer_class = RoleOnboardSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.user.role != User.Role.CUSTOMER:
            return Response({"detail": "Role already assigned."}, status=status.HTTP_409_CONFLICT)
        request.user.role = serializer.validated_data["role"]
        request.user.save(update_fields=["role"])
        return Response(UserSerializer(request.user).data)


class LoginView(generics.GenericAPIView):
    serializer_class = TokenObtainSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (LoginThrottle,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutAllView(generics.GenericAPIView):
    class _DummySerializer(serializers.Serializer):
        pass

    serializer_class = _DummySerializer

    def post(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.bump_token_version()
        return Response({"detail": "Logged out from all devices."}, status=status.HTTP_200_OK)


class GoogleLoginView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        client_id = settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"]
        redirect_uri = f"{request.scheme}://{request.get_host()}/api/auth/google/login/callback/"
        google_auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&redirect_uri={redirect_uri}"
            "&response_type=code&scope=openid%20email%20profile"
        )
        return redirect(google_auth_url)


def _send_reset_otp_email(to_email, code):
    """Deliver the OTP email as plain text plus a styled HTML alternative."""
    context = {
        "site_name": "PlateRoute",
        "email": to_email,
        "code": code,
        "code_chars": list(code),
        "ttl_minutes": PasswordResetOTP.TTL_MINUTES,
    }
    message = EmailMultiAlternatives(
        subject=f"Your {context['site_name']} password reset code",
        body=render_to_string("emails/password_reset_otp.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(
        render_to_string("emails/password_reset_otp.html", context), "text/html"
    )
    message.send(fail_silently=False)


class PasswordResetOTPRequestView(generics.GenericAPIView):
    """Emails an 8-character OTP (digits + letters + specials) to the user."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = PasswordResetOTPRequestSerializer
    throttle_classes = (PasswordResetRequestThrottle,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        debug_code = None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal whether the email exists.
            pass
        else:
            _, raw_code = PasswordResetOTP.issue(user)
            try:
                _send_reset_otp_email(user.email, raw_code)
            except Exception:
                # Email backend failures must not leak account existence.
                logger.exception("Failed to send password-reset OTP to %s", user.email)
            else:
                if settings.DEBUG:
                    # Dev convenience only — never set DJANGO_DEBUG=true in production.
                    debug_code = raw_code

        data = {"detail": GENERIC_RESET_MESSAGE}
        if debug_code:
            data["debug_otp"] = debug_code
        return Response(data, status=status.HTTP_200_OK)


class PasswordResetOTPConfirmView(generics.GenericAPIView):
    """Verifies the emailed OTP and sets the new password."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = PasswordResetOTPConfirmSerializer
    throttle_classes = (PasswordResetConfirmThrottle,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

        record = (
            user.password_otps.filter(code_hash=hash_otp(otp), used=False)
            .order_by("-created_at")
            .first()
        )
        if record is None or not record.is_valid():
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

        # Atomically consume the code so it cannot be reused, even under
        # concurrent requests hitting the same code.
        claimed = PasswordResetOTP.objects.filter(pk=record.pk, used=False).update(used=True)
        if not claimed:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        # Invalidate any other outstanding codes and log out every device by
        # bumping the token version (same mechanism as LogoutAllView).
        user.password_otps.filter(used=False).update(used=True)
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.bump_token_version()

        return Response({"detail": "Password has been reset."}, status=status.HTTP_200_OK)
