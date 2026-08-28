from unittest import mock

from django.test import TestCase

from calls.models import CallEvent, CallSession
from .helpers import api, make_user


class CallTests(TestCase):
    """"§11": start/answer/end lifecycle, abuse lock, TURN credentials."""

    def setUp(self):
        self.alice = make_user("alice@test.io")
        self.bob = make_user("bob@test.io", role="courier")

    def _start(self):
        return api(self.alice, "post", "/v1/calls/", {"action": "start", "callee_user": self.bob.id})

    def test_lifecycle_ring_accept_end(self):
        start = self._start()
        self.assertEqual(start.status_code, 200)
        call_id = start.json()["call_id"]
        self.assertEqual(CallSession.objects.get(pk=call_id).status, "ringing")
        # callee accepts, initiator cannot accept (only callee)
        self.assertEqual(api(self.alice, "post", f"/v1/calls/{call_id}/", {"action": "accept"}).status_code, 403)
        res = api(self.bob, "post", f"/v1/calls/{call_id}/", {"action": "accept"})
        self.assertEqual(res.json()["status"], "accepted")
        # end from either party
        res = api(self.bob, "post", f"/v1/calls/{call_id}/", {"action": "end"})
        self.assertEqual(res.json()["status"], "ended")
        self.assertTrue(CallEvent.objects.filter(session_id=call_id).count() >= 3)

    def test_single_active_call_lock(self):
        self._start()
        res = api(self.bob, "post", "/v1/calls/", {"action": "start", "callee_user": self.alice.id})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "call.active_already")

    def test_decline_by_callee(self):
        call_id = self._start().json()["call_id"]
        res = api(self.bob, "post", f"/v1/calls/{call_id}/", {"action": "decline"})
        self.assertEqual(res.json()["status"], "declined")

    def test_turn_credentials_hmac(self):
        with mock.patch.dict("os.environ", {"TURN_STATIC_AUTH_SECRET": "s3cret", "TURN_URLS": "turn:1.2.3.4:3478"}):
            res = api(self.alice, "get", "/v1/calls/turn-credentials/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["username"].startswith(f"{self.alice.id}:"))
        self.assertTrue(res.json()["credential"])