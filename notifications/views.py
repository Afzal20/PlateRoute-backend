from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeviceRegistry, NotificationPreference


class DeviceRegistryView(APIView):
    """FR-NOT-02 / MOB-C-02: upsert an FCM token for push."""

    def post(self, request):
        token = request.data.get("fcm_token", "")
        if not token:
            return Response({"detail": "fcm_token required"}, status=400)
        device, _ = DeviceRegistry.objects.get_or_create(
            fcm_token=token, defaults=dict(user=request.user,
                                           platform=request.data.get("platform", "android"),
                                           app_version=request.data.get("app_version", "")))
        device.user = request.user
        device.save(update_fields=["user"])
        return Response({"registered": True})


class PreferenceView(APIView):
    """FR-AUTH-10: per-channel notification toggles."""

    def get(self, request):
        prefs = {p.kind: {"email": p.email, "push": p.push, "sms": p.sms}
                 for p in NotificationPreference.objects.filter(user=request.user)}
        return Response(prefs)

    def post(self, request):
        kind = request.data.get("kind")
        if kind not in NotificationPreference.Kind.values:
            return Response({"detail": "unknown kind"}, status=400)
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user, kind=kind)
        for field in ("email", "push", "sms"):
            if field in request.data:
                setattr(pref, field, bool(request.data[field]))
        pref.save()
        return Response({"kind": pref.kind, "email": pref.email, "push": pref.push, "sms": pref.sms})