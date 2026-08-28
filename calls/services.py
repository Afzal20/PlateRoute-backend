"""Call scope windows and event recording (§11)."""
from django.db.models import Q
from django.utils import timezone as tz
from rest_framework import status

from common.errors import DomainError

from .models import CallEvent, CallSession


def now():
    return tz.now()


def window_open(caller, callee):
    """§11 abuse guards: no overlapping live call for either party."""
    live = [CallSession.Status.RINGING, CallSession.Status.ACCEPTED]
    for user in (caller, callee):
        if CallSession.objects.filter(Q(initiator=user) | Q(callee=user), status__in=live, ended_at__isnull=True).exists():
            raise DomainError("call.active_already", "You already have an active call.", status.HTTP_409_CONFLICT)


def record_event(session, event_type, *, source="app", **payload):
    return CallEvent.objects.create(session=session, type=event_type, source=source, payload=payload)