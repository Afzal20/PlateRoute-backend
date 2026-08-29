from django.core.management.base import BaseCommand

from analytics import services


class Command(BaseCommand):
    """Celery-beat equivalent: nightly KPI rebuild (FR-REP-03)."""

    help = "Rebuild daily branch analytics aggregates."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=1)

    def handle(self, *args, **options):
        built = services.rebuild_daily(days=options["days"])
        self.stdout.write(f"rebuilt {built} branch metric row(s)")