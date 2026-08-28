"""Transactional outbox funnel: enqueue + worker pump (FR-NOT-01..02)."""
from django.conf import settings
from django.utils import timezone

from common.errors import DomainError
from rest_framework import status

from .models import NotificationOutbox, NotificationTemplate


def enqueue(*, code, user=None, recipient="", context=None, dedup_key=""):
    """Create a queued outbox row; a worker renders + sends it (at-least-once)."""
    template = NotificationTemplate.objects.filter(code=code, active=True).first()
    if not template:
        raise DomainError("notify.unknown_template", f"No active template '{code}'.", status.HTTP_400_BAD_REQUEST)
    outbox, created = None, False
    if dedup_key:
        outbox, created = NotificationOutbox.objects.get_or_create(
            dedup_key=dedup_key, defaults=dict(
                channel=template.channel, recipient_user=user, recipient=recipient or "",
                template=template, context=context or {}, scheduled_at=timezone.now()))
    else:
        outbox = NotificationOutbox.objects.create(
            channel=template.channel, recipient_user=user, recipient=recipient or "",
            template=template, context=context or {}, scheduled_at=timezone.now())
    return outbox


def deliver(outbox):
    """Render template and hand off to the channel adapter (no-op worker stub)."""
    outbox.attempts += 1
    outbox.state = NotificationOutbox.State.SENDING
    outbox.save(update_fields=["attempts", "state"])
    try:
        rendered = outbox.template.body.format(**outbox.context) if outbox.template else ""
        # Channel adapters (email/push/sms) plug here; console write keeps parity
        # with the existing dev email backend.
        if outbox.channel == "email" and outbox.recipient_user:
            from django.core.mail import send_mail
            send_mail(outbox.template.subject or "PlateRoute", rendered,
                      settings.DEFAULT_FROM_EMAIL, [outbox.recipient_user.email], fail_silently=True)
        outbox.state = NotificationOutbox.State.SENT
        outbox.sent_at = timezone.now()
    except Exception:
        outbox.state = NotificationOutbox.State.FAILED
    outbox.save(update_fields=["state", "sent_at", "attempts"])
    return outbox.state


def render(outbox):
    return outbox.template.body.format(**outbox.context) if outbox.template else ""