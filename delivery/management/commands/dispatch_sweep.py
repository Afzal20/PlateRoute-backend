from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from common.models import RuntimeConfig
from delivery.models import LocationPing
from delivery.services import sweep_expired


class Command(BaseCommand):
    """Dispatch timers: offer expiry cascade + 30-day ping retention (NFR-13)."""

    help = "Sweep expired delivery offers and prune old location pings."

    def handle(self, *args, **options):
        swept = sweep_expired()
        cutoff = timezone.now() - timedelta(days=RuntimeConfig.get("delivery.ping_retention_days", 30))
        pruned, _ = LocationPing.objects.filter(recorded_at__lt=cutoff).delete()
        self.stdout.write(f"swept {swept} task(s), pruned {pruned} ping(s)")
