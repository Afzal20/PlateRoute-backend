from drf_spectacular.extensions import OpenApiAuthenticationExtension

from .authentication import VersionedJWTAuthentication


class VersionedJWTExtension(OpenApiAuthenticationExtension):
    target_class = VersionedJWTAuthentication
    name = "JWTAuth"
    priority = 1

    def get_security_definition(self, schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
