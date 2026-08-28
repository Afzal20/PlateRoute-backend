from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from delivery.models import CourierProfile, DeliveryOffer, DeliveryTask, LocationPing
from orders.models import Order
from .helpers import api, make_user
from .test_orders import make_address, seed_cart


class DeliveryFlowTests(TestCase):
    """FR-DLV-01..04: dispatch -> offer -> claim -> trip -> tracking."""

    def setUp(self):
        self.user = make_user()
        self.branch, self.item = seed_cart(self.user)
        self.address = make_address(self.user)
        api(self.user, "post", "/v1/orders/place/", {"address": str(self.address.uuid)})
        self.order = Order.objects.get()
        # two online couriers with pings near the branch
        self.near = self._courier("near@test.io", 23.80, 90.40)
        self.far = self._courier("far@test.io", 23.90, 90.60)

    def _courier(self, email, lat, lng):
        profile = CourierProfile.objects.create(user=make_user(email, role="courier"), is_online=True)
        LocationPing.objects.create(courier=profile, lat=lat, lng=lng)
        return profile

    def _drive_to_ready(self):
        vendor = self.branch.vendor.owner
        for status in ("accepted", "preparing", "ready"):
            api(vendor, "post", f"/v1/orders/{self.order.uuid}/transition/", {"to_status": status})
        self.order.refresh_from_db()

    def test_profile_and_shift(self):
        res = api(self.near.user, "put", "/v1/delivery/profile/", {"online": False, "vehicle": "car"})
        self.assertFalse(res.json()["is_online"])

    def test_dispatch_creates_task_and_offers_nearest_first(self):
        self._drive_to_ready()
        call_command("pump_outbox")
        task = DeliveryTask.objects.get(order=self.order)
        self.assertEqual(task.state, "offering")
        offers = list(DeliveryOffer.objects.filter(task=task).order_by("id"))
        self.assertEqual([o.courier for o in offers], [self.near, self.far])  # nearest ranked first
        # courier sees only his live offer
        visible = api(self.far.user, "get", "/v1/delivery/offers/").json()
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0]["fee_minor"], task.courier_fee_minor)

    def test_claim_single_winner_and_trip_to_delivered(self):
        self._drive_to_ready()
        call_command("pump_outbox")
        offer_near = DeliveryOffer.objects.get(courier=self.near)
        offer_far = DeliveryOffer.objects.get(courier=self.far)
        # far courier cannot claim near's offer
        res = api(self.far.user, "post", "/v1/delivery/offers/{}/claim/".format(offer_near.id))
        self.assertEqual(res.status_code, 409)
        res = api(self.near.user, "post", f"/v1/delivery/offers/{offer_near.id}/claim/")
        self.assertEqual(res.json()["state"], "claimed")
        # loser offer now expired; second claim attempt fails
        offer_far.refresh_from_db()
        self.assertEqual(offer_far.state, "expired")
        res = api(self.near.user, "post", "/v1/delivery/offers/{}/claim/".format(DeliveryOffer.objects.get(courier=self.near).id))
        self.assertEqual(res.status_code, 409)
        # trip drives the order through picked/out/delivered
        task = DeliveryTask.objects.get(order=self.order)
        for action in ("at_vendor", "picked", "arrived", "dropped"):
            res = api(self.near.user, "post", f"/v1/delivery/tasks/{task.uuid}/trip/", {"action": action})
            self.assertEqual(res.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "delivered")

    def test_tracking_participants_only(self):
        self._drive_to_ready()
        call_command("pump_outbox")
        offer = DeliveryOffer.objects.get(courier=self.near)
        api(self.near.user, "post", f"/v1/delivery/offers/{offer.id}/claim/")
        api(self.near.user, "post", "/v1/delivery/pings/", {"pings": [{"lat": 23.81, "lng": 90.41, "speed": 5}]})
        data = api(self.user, "get", f"/v1/delivery/orders/{self.order.uuid}/tracking/").json()
        self.assertEqual(data["courier_location"], [23.81, 90.41])
        outsider = make_user("x@test.io")
        self.assertEqual(api(outsider, "get", f"/v1/delivery/orders/{self.order.uuid}/tracking/").status_code, 403)

    def test_offer_expiry_cascade(self):
        from datetime import timedelta
        self._drive_to_ready()
        call_command("pump_outbox")
        task = DeliveryTask.objects.get(order=self.order)
        DeliveryOffer.objects.filter(courier=self.near).update(state="declined")  # near declines round 1
        DeliveryOffer.objects.filter(courier=self.far).update(expires_at=timezone.now() - timedelta(seconds=1))
        call_command("dispatch_sweep")
        task.refresh_from_db()
        self.assertEqual(task.state, "offering")
        fresh = DeliveryOffer.objects.get(task=task, courier=self.far, state="sent")
        self.assertGreater(fresh.expires_at, timezone.now())  # far re-armed, near declined stays out