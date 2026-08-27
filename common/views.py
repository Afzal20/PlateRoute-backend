from django.core.cache import cache
from django.db import connection
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RuntimeConfig


class HealthView(APIView):
    """/healthz liveness probing database and cache."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        try:
            connection.ensure_connection()
            db_ok = True
        except Exception:
            db_ok = False
        try:
            cache.set("healthz", "1", 5)
            cache_ok = cache.get("healthz") == "1"
        except Exception:
            cache_ok = False
        healthy = db_ok and cache_ok
        return Response({"db": db_ok, "cache": cache_ok}, status=200 if healthy else 503)


class ConfigView(APIView):
    """Public client-facing config: ?key=a&key=b -> {a: .., b: ..}."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        return Response({k: RuntimeConfig.get(k) for k in request.GET.getlist("key")})
