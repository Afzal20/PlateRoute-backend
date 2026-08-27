from django.core.management import call_command
from django.test import TestCase

from common.events import HANDLERS, on
from common.errors import DomainError, handler
from common.geo import haversine_m
from common.models import OutboxMessage, RuntimeConfig


class ErrorHandlingTests(TestCase):
    def test_domain_error_envelope(self):
        response = handler(DomainError("order.closed", "nope"), context=None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"detail": "nope", "code": "order.closed"})


class RuntimeConfigTests(TestCase):
    def test_get_default_and_overrides(self):
        self.assertIsNone(RuntimeConfig.get("missing"))
        self.assertEqual(RuntimeConfig.get("missing", 7), 7)
        RuntimeConfig.objects.create(key="delivery.fee", value=5000)
        self.assertEqual(RuntimeConfig.get("delivery.fee"), 5000)


class GeoTests(TestCase):
    def test_haversine_zero_and_known(self):
        self.assertEqual(haversine_m((23.8, 90.4), (23.8, 90.4)), 0)
        self.assertGreater(haversine_m((23.8, 90.4), (23.7, 90.4)), 10000)


class OutboxTests(TestCase):
    def test_emit_and_pump_delivers_to_handler(self):
        seen = []
        on("test.ping")(lambda payload: seen.append(payload))
        OutboxMessage.emit("test.ping", order=1)
        OutboxMessage.emit("test.unhandled", order=2)
        call_command("pump_outbox")
        self.assertEqual(seen, [{"order": 1}])
        self.assertFalse(OutboxMessage.objects.filter(processed_at__isnull=True).exists())
        HANDLERS.pop("test.ping")
