from django.core.management.base import BaseCommand
from django.utils import timezone

from common.events import HANDLERS
from common.models import OutboxMessage


class Command(BaseCommand):
    help = "Deliver unprocessed OutboxMessage rows to registered handlers."

    def handle(self, *args, **options):
        pending = OutboxMessage.objects.filter(processed_at__isnull=True).order_by("created_at")
        count = failures = 0
        for msg in pending:
            for handler in HANDLERS.get(msg.kind, []):
                try:
                    handler(msg.payload)
                except Exception as exc:  # a bad event never starves the queue
                    failures += 1
                    self.stderr.write(f"handler for {msg.kind} failed: {exc}")
            msg.processed_at = timezone.now()
            msg.save(update_fields=["processed_at"])
            count += 1
        self.stdout.write(f"pumped {count} outbox message(s){f' ({failures} handler failure(s))' if failures else ''}")
