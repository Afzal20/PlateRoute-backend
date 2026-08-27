from django.core.management.base import BaseCommand
from django.utils import timezone

from common.events import HANDLERS
from common.models import OutboxMessage


class Command(BaseCommand):
    help = "Deliver unprocessed OutboxMessage rows to registered handlers."

    def handle(self, *args, **options):
        pending = OutboxMessage.objects.filter(processed_at__isnull=True).order_by("created_at")
        count = 0
        for msg in pending:
            for handler in HANDLERS.get(msg.kind, []):
                handler(msg.payload)
            msg.processed_at = timezone.now()
            msg.save(update_fields=["processed_at"])
            count += 1
        self.stdout.write(f"pumped {count} outbox message(s)")
