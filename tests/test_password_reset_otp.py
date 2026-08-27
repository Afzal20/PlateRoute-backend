"""Tests for the OTP-based password reset flow."""

from datetime import timedelta

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import PasswordResetOTP, Profile, User
from accounts.otp import ALL_OTP_CHARS, OTP_LENGTH, OTP_SPECIALS, generate_otp, hash_otp
from accounts.views import GENERIC_RESET_MESSAGE


REQUEST_URL_NAME = "password_reset_otp"
CONFIRM_URL_NAME = "password_reset_otp_confirm"

OLD_PASSWORD = "OldSecret123!"
NEW_PASSWORD = "Fresh-Secret-456!"


def extract_code_from_email(body):
    """The raw code sits on its own line right after 'Your password reset code is:'."""
    lines = [line.strip() for line in body.splitlines()]
    idx = lines.index("Your password reset code is:")
    return lines[idx + 2]


class GenerateOTPTests(TestCase):
    def test_length_is_eight_with_required_mix(self):
        for _ in range(200):
            code = generate_otp()
            self.assertEqual(len(code), OTP_LENGTH)
            self.assertTrue(any(c.isdigit() for c in code), code)
            self.assertTrue(any(c.isalpha() for c in code), code)
            self.assertTrue(any(c in OTP_SPECIALS for c in code), code)
            self.assertTrue(all(c in ALL_OTP_CHARS for c in code), code)

    def test_hashing_is_case_and_whitespace_insensitive(self):
        code = generate_otp()
        self.assertEqual(hash_otp(code), hash_otp(code.swapcase()))
        self.assertEqual(hash_otp(code), hash_otp(f" {code}\t"))
        self.assertNotEqual(hash_otp(code), hash_otp(code[:-1] + "*"))

    def test_codes_are_random(self):
        seen = {generate_otp() for _ in range(100)}
        self.assertGreater(len(seen), 90)


class PasswordResetOTPFlowTests(TestCase):
    def setUp(self):
        cache.clear()  # isolate anon-throttle counters between tests
        self.email = "resetme@example.com"
        self.user = User.objects.create_user(email=self.email, password=OLD_PASSWORD)
        self.profile = Profile.objects.get(user=self.user)

    # -- helpers ---------------------------------------------------------
    def _request_otp(self):
        emails_before = len(mail.outbox)
        response = self.client.post(reverse(REQUEST_URL_NAME), {"email": self.email})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], GENERIC_RESET_MESSAGE)
        self.assertEqual(len(mail.outbox), emails_before + 1)
        self.assertIn(self.email, mail.outbox[-1].to)
        return extract_code_from_email(mail.outbox[-1].body)

    def _confirm(self, otp, password=NEW_PASSWORD, email=None):
        return self.client.post(
            reverse(CONFIRM_URL_NAME),
            {"email": email or self.email, "otp": otp, "new_password": password},
        )

    def _latest_record(self):
        return PasswordResetOTP.objects.order_by("-created_at").first()

    # -- OTP request endpoint -------------------------------------------
    def test_request_emails_mixed_code_and_stores_only_hash(self):
        code = self._request_otp()
        self.assertEqual(len(code), OTP_LENGTH)
        self.assertTrue(any(c.isdigit() for c in code))
        self.assertTrue(any(c.isalpha() for c in code))
        self.assertTrue(any(c in OTP_SPECIALS for c in code))

        record = self._latest_record()
        self.assertNotEqual(record.code_hash, code)  # never store plaintext
        self.assertEqual(record.code_hash, hash_otp(code))
        self.assertFalse(record.used)

    def test_new_request_invalidates_previous_code(self):
        first_code = self._request_otp()
        second_code = self._request_otp()
        self.assertNotEqual(first_code, second_code)
        self.assertEqual(
            PasswordResetOTP.objects.filter(used=False).count(),
            1,
            "only the newest code may remain outstanding",
        )
        response = self._confirm(first_code)
        self.assertEqual(response.status_code, 400)

    def test_request_for_unknown_email_does_not_leak_or_send(self):
        response = self.client.post(reverse(REQUEST_URL_NAME), {"email": "ghost@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], GENERIC_RESET_MESSAGE)
        self.assertEqual(len(mail.outbox), 0)
        self.assertNotIn("debug_otp", response.json())

    # -- OTP confirm endpoint -------------------------------------------
    def test_full_flow_resets_password_and_logs_out_devices(self):
        version_before = self.profile.token_version
        code = self._request_otp()

        response = self._confirm(code)
        self.assertEqual(response.status_code, 200, response.content)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertFalse(self.user.check_password(OLD_PASSWORD))
        self.assertEqual(self.profile.token_version, version_before + 1)
        self.assertEqual(PasswordResetOTP.objects.filter(used=False).count(), 0)

    def test_login_works_with_new_password_after_reset(self):
        code = self._request_otp()
        self.assertEqual(self._confirm(code).status_code, 200)

        response = self.client.post(
            reverse("login"), {"email": self.email, "password": NEW_PASSWORD}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("access", response.json())

    def test_wrong_code_rejected_and_password_untouched(self):
        self._request_otp()
        response = self._confirm("XyZ9!Ab#")  # valid shape, wrong value
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))

    def test_expired_code_rejected(self):
        self._request_otp()
        record = self._latest_record()
        record.expires_at = timezone.now() - timedelta(seconds=1)
        record.save(update_fields=["expires_at"])

        response = self._confirm(extract_code_from_email(mail.outbox[0].body))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid or expired code", response.json()["detail"])

    def test_code_cannot_be_reused(self):
        code = self._request_otp()
        self.assertEqual(self._confirm(code).status_code, 200)
        response = self._confirm(code.replace("#", "@"))
        self.assertEqual(response.status_code, 400)

    def test_confirmation_accepts_different_case_and_surrounding_spaces(self):
        code = self._request_otp()
        response = self._confirm(f"  {code.swapcase()} ")
        self.assertEqual(response.status_code, 200, response.content)

    def test_unknown_email_gets_same_generic_error_as_bad_code(self):
        response_unknown = self._confirm("AaBb12#$", email="ghost@example.com")
        response_bad_code = self._confirm("AaBb12#$")
        self.assertEqual(response_unknown.status_code, 400)
        self.assertEqual(response_unknown.json()["detail"], response_bad_code.json()["detail"])

    def test_weak_new_password_fails_without_consuming_code(self):
        code = self._request_otp()
        response = self._confirm(code, password="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("new_password", response.json())

        # The code was not consumed by the failed attempt.
        retry = self._confirm(code)
        self.assertEqual(retry.status_code, 200, retry.content)


class PasswordResetOTPEmailTemplateTests(TestCase):
    """Covers the branded OTP email (plain text + styled HTML alternative)."""

    def setUp(self):
        cache.clear()
        self.email = "template@example.com"

    def _send(self, code="AaB3&E5#"):
        from accounts.views import _send_reset_otp_email

        _send_reset_otp_email(self.email, code)
        self.assertEqual(len(mail.outbox), 1)
        return mail.outbox[0]

    def test_message_has_text_part_and_html_alternative(self):
        msg = self._send()
        self.assertEqual(msg.subject, "Your PlateRoute password reset code")
        self.assertEqual(msg.to, [self.email])
        # The existing email-parsing helper keeps working off the text part.
        self.assertEqual(extract_code_from_email(msg.body), "AaB3&E5#")
        self.assertEqual(len(msg.alternatives), 1)
        html, mime_type = msg.alternatives[0]
        self.assertEqual(mime_type, "text/html")

    def test_html_shows_every_character_and_escapes_specials(self):
        code = "AaB3&E5#"
        msg = self._send(code)
        html = msg.alternatives[0][0]

        # '&' inside codes is escaped by autoescape — never rendered raw.
        self.assertIn("AaB3&amp;E5#", html)
        self.assertNotIn("AaB3&E5#", html)
        # One bordered tile per character.
        self.assertEqual(html.count('class="code-char"'), len(code))
        # Tap-to-select copy line + validity info are present.
        self.assertIn("user-select:all", html)
        self.assertIn(f"Expires in {PasswordResetOTP.TTL_MINUTES} minutes", html)
        self.assertIn("Works only once", html)

    def test_plain_text_contains_usage_guidance(self):
        body = self._send().body
        lowered = body.lower()
        for fragment in (
            "your password reset code is:",
            "can only be used once",
            "case-insensitive",
            f"{PasswordResetOTP.TTL_MINUTES} minutes",
            "didn't request",
        ):
            self.assertIn(fragment, lowered)

