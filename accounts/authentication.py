from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Profile


class VersionedJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        user_id = token.get("user_id")
        token_version = token.get("token_version", 0)

        try:
            profile = Profile.objects.get(user_id=user_id)
        except Profile.DoesNotExist:
            raise AuthenticationFailed("Session invalidated.")

        if profile.token_version != token_version:
            raise AuthenticationFailed("Session invalidated. Please login again.")
        return token
