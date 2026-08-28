from django.core.management import call_command
from django.test import TestCase

from chat.models import Participant, Thread
from delivery.models import CourierProfile
from orders.models import Order
from .helpers import api, make_user
from .test_orders import make_address, seed_cart


class ChatTests(TestCase):
    """"§10": order thread bootstrap, participant watermarks, scoped send."""

    def setUp(self):
        self.customer = make_user()
        self.branch, self.item = seed_cart(self.customer)
        self.vendor_user = self.branch.vendor.owner
        self.address = make_address(self.customer)
        api(self.customer, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        self.order = Order.objects.get()
        bootstrap = api(self.customer, "post", "/v1/chat/threads/", {"order": str(self.order.uuid)})
        self.thread_uuid = bootstrap.json()["uuid"]
        self.thread = Thread.objects.get()

    def test_bootstrap_members_and_dm_flow(self):
        self.assertEqual(set(Participant.objects.filter(thread=self.thread).values_list("role", flat=True)),
                         {"customer", "vendor_staff"})
        # send from customer, read by vendor
        sent = api(self.customer, "post", f"/v1/chat/threads/{self.thread_uuid}/send/", {"body": "Halal makes sure?"})
        self.assertEqual(sent.status_code, 201)
        # unread seen by vendor
        msg = api(self.vendor_user, "get", f"/v1/chat/threads/{self.thread_uuid}/messages/").json()["messages"]
        self.assertEqual(msg[0]["body"], "Halal makes sure?")
        lists = api(self.vendor_user, "get", "/v1/chat/threads/").json()
        self.assertEqual(lists[0]["unread"], 1)
        # marking read drops unread to 0
        read = api(self.vendor_user, "post", f"/v1/chat/threads/{self.thread_uuid}/read/", {"message_id": msg[0]["id"]})
        self.assertEqual(read.json()["unread"], 0)

    def test_non_participant_rejected(self):
        outsider = make_user("x@test.io")
        res = api(outsider, "post", f"/v1/chat/threads/{self.thread_uuid}/send/", {"body": "spam"})
        self.assertEqual(res.status_code, 403)

    def test_flag_and_empty_body(self):
        res = api(self.customer, "post", f"/v1/chat/threads/{self.thread_uuid}/send/", {"body": "   "})
        self.assertEqual(res.json()["code"], "chat.empty")
        sent = api(self.customer, "post", f"/v1/chat/threads/{self.thread_uuid}/send/", {"body": "please flag me"})
        res = api(self.vendor_user, "post", f"/v1/chat/threads/{self.thread_uuid}/report/", {"message_id": sent.json()["id"], "reason": "abuse"})
        self.assertEqual(res.status_code, 201)

    def test_courier_joins_when_task_claimed_and_picked(self):
        # courier claims the ready task -> thread picks them up
        courier = CourierProfile.objects.create(user=make_user("c@test.io", role="courier"), is_online=True)
        for status in ("accepted", "preparing", "ready"):
            api(self.vendor_user, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": status})
        call_command("pump_outbox")
        from delivery.models import DeliveryOffer, DeliveryTask
        task = DeliveryTask.objects.get(order=self.order)
        offer = DeliveryOffer.objects.get(task=task, courier=courier)
        api(courier.user, "post", f"/v1/delivery/offers/{offer.id}/claim/")
        api(courier.user, "post", f"/v1/delivery/tasks/{task.uuid}/trip/", {"action": "picked"})
        call_command("pump_outbox")
        self.thread.refresh_from_db()
        roles = set(Participant.objects.filter(thread=self.thread).values_list("role", flat=True))
        self.assertIn("courier", roles)