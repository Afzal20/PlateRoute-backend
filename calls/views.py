from uuid import uuid4

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import DomainError

from . import services
from .models import CallEvent, CallSession


class CallView(APIView):
    """Start/accept/decline/end a 1:1 data-voice call (§11)."""

    def post(self, request, pk=None):
        User = get_user_model()
        action = request.data.get("action", "start")
        if action == "start":
            callee = User.objects.filter(id=request.data.get("callee_user")).first()
            if not callee:
                raise DomainError("call.callee_required", "Unknown target user.", status.HTTP_400_BAD_REQUEST)
            services.window_open(request.user, callee)
            session = CallSession.objects.create(
                initiator=request.user, callee=callee,
                scope_object=f"initiator:{request.user.id}->{callee.id}",
                room_name=f"call-{uuid4().hex[:12]}")
            services.record_event(session, CallEvent.Type.RUNG)
            return Response({"call_id": session.id, "room": session.room_name,
                             "status": session.status, "callee": callee.email})
        session = CallSession.objects.filter(pk=pk).first()
        if not session:
            raise DomainError("call.not_found", "Call not found.", status.HTTP_404_NOT_FOUND)
        return self._state_change(request, session, action)

    @staticmethod
    def _state_change(request, session, action):
        user = request.user
        is_party = user.id in (session.initiator_id, session.callee_id)
        if not is_party and not (user.is_staff or user.role == "operator"):
            raise DomainError("call.forbidden", "Not a call participant.", status.HTTP_403_FORBIDDEN)
        if action in ("accept", "decline") and session.callee_id != user.id:
            raise DomainError("call.only_callee", "Only the callee can answer.", status.HTTP_403_FORBIDDEN)
        if action == "accept":
            if session.status != CallSession.Status.RINGING:
                raise DomainError("call.not_ringing", "This call is no longer ringing.", status.HTTP_409_CONFLICT)
            session.status, session.connected_at = CallSession.Status.ACCEPTED, services.now()
            services.record_event(session, CallEvent.Type.ACCEPTED)
        elif action == "decline":
            session.status, session.end_reason = CallSession.Status.DECLINED, "declined"
            session.ended_at = services.now()
            services.record_event(session, CallEvent.Type.DECLINED)
        elif action in ("end", "cancel", "miss"):
            session.status = CallSession.Status.ENDED if action == "end" else CallSession.Status.MISSED
            session.ended_at, session.end_reason = services.now(), action
            services.record_event(session, CallEvent.Type.ROOM_ENDED)
        else:
            raise DomainError("call.bad_action", "Unknown call action.")
        session.save()
        return Response({"call_id": session.id, "status": session.status, "room": session.room_name})


class TurnCredentialsView(APIView):
    """TURN REST API ephemeral credentials (HMAC over username-ttl, §11)."""

    def get(self, request):
        import base64
        import hashlib
        import hmac
        import os
        import time
        ttl = 3600
        uname = f"{request.user.id}:{int(time.time()) + ttl}"
        secret = os.environ.get("TURN_STATIC_AUTH_SECRET", "")
        if not secret:
            raise DomainError("call.turn_unconfigured", "TURN credentials are not configured.")
        token = hmac.new(secret.encode(), uname.encode(), hashlib.sha1).digest()
        return Response({"username": uname, "credential": base64.b64encode(token).decode(),
                         "ttl": ttl, "urls": os.environ.get("TURN_URLS", "turn:127.0.0.1:3478")})