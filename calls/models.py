from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class CallSession(TimeStampedModel):
    """§11: metadata-only call lifecycle; media travels over LiveKit."""

    class Status(models.TextChoices):
        RINGING = "ringing", "Ringing"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        BUSY = "busy", "Busy"
        MISSED = "missed", "Missed"
        ENDED = "ended", "Ended"
        FAILED = "failed", "Failed"

    thread = models.ForeignKey("chat.Thread", null=True, blank=True, on_delete=models.CASCADE, related_name="calls")
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calls_initiated")
    callee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calls_received")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RINGING)
    scope_object = models.CharField(max_length=60, blank=True)  # e.g. "order:<uuid>"
    connected_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=100, blank=True)
    room_name = models.CharField(max_length=40, unique=True)

    def __str__(self):
        return f"call {self.room_name} [{self.status}]"


class CallEvent(models.Model):
    class Type(models.TextChoices):
        INVITE_SENT = "invite_sent", "Invite sent"
        RUNG = "rung", "Rung"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        BUSY = "busy", "Busy"
        MEDIA_CONNECTED = "media_connected", "Media connected"
        PARTICIPANT_LEFT = "participant_left", "Participant left"
        ROOM_ENDED = "room_ended", "Room ended"

    session = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name="events")
    type = models.CharField(max_length=20, choices=Type.choices)
    payload = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=12, default="app")  # app | livekit_webhook
    occurred_at = models.DateTimeField(auto_now_add=True)