from django.core.management import call_command
from django.test import TestCase

from notifications.models import NotificationOutbox, NotificationTemplate
from .helpers import api, make_user
from .test_orders import make_address, seed_cart


class NotificationTests(TestCase):
    """"FR-NOT-01/02 + FR-AUTH-10": outbox funnel, devices, preferences."""

    def setUp(self):
        self.template = NotificationTemplate.objects.create(
            code="order_placed_vendor", channel="email", subject="Order {order_pk}",
            body="You have order #{order_pk} for ${total}.")
        self.user = make_user("notif@test.io")

    def test_enqueue_and_send_via_worker(self):
        outbox = NotificationOutbox.objects.create(
            channel="email", recipient_user=self.user, template=self.template,
            context={"order_pk": 7, "total": 5000})
        call_command("send_notifications")
        outbox.refresh_from_db()
        self.assertEqual(outbox.state, "sent")
        self.assertIn("order #7", outbox.template.body.format(**{"order_pk": 7, "total": 5000}))

    def test_dedup_key_only_sends_once(self):
        from notifications import services
        services.enqueue(code="order_placed_vendor", user=self.user, context={"order_pk": 1},
                         dedup_key="k")
        services.enqueue(code="order_placed_vendor", user=self.user, context={"order_pk": 1},
                         dedup_key="k")
        self.assertEqual(NotificationOutbox.objects.filter(dedup_key="k").count(), 1)

    def test_envoutbox_vendor_alert_on_placement(self):
        customer = make_user()
        branch, _ = seed_cart(customer)
        address = make_address(customer)
        api(customer, "post", "/v1/orders/place/", {"address": str(address.uuid)})
        call_command("pump_outbox")
        self.assertTrue(NotificationOutbox.objects.filter(recipient_user=branch.vendor.owner).exists())

    def test_devices_and_preferences(self):
        res = api(self.user, "post", "/v1/notifications/devices/", {"fcm_token": "tok-1", "platform": "android"})
        self.assertEqual(res.json()["registered"], True)
        res = api(self.user, "post", "/v1/notifications/preferences/", {"kind": "order_updates", "push": False})
        self.assertFalse(res.json()["push"])
        prefs = api(self.user, "get", "/v1/notifications/preferences/").json()
        self.assertIn("order_updates", prefs)