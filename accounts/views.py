from django.conf import settings
from django.shortcuts import redirect
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response

from .models import Profile, User
from .serializers import RegisterSerializer, UserSerializer, TokenObtainSerializer
from .throttles import LoginThrottle, RegisterThrottle


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (RegisterThrottle,)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


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
