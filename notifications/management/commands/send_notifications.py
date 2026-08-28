from django.core.management.base import BaseCommand

from notifications.models import NotificationOutbox
from notifications.services import deliver


class Command(BaseCommand):
    """Pump queued notification outbox rows through the channel adapters."""

    help = "Send pending notifications (transactional email / push / sms)."

    def handle(self, *args, **options):
        pending = NotificationOutbox.objects.filter(state__in=["queued", "sending"])
        done = 0
        for outbox in pending:
            deliver(outbox)
            done += 1
        self.stdout.write(f"processed {done} notification(s)")