"""Live API smoke test for PlateRoute backend (run against a running dev server).

Reuses helpers from backend/tests/test_external.py and extends them with:
- public endpoints (healthz, OpenAPI schema, discovery)
- vendor onboarding flow (role onboard -> vendor -> branch -> submit -> 409 resubmit)
- OTP password reset using the code parsed from the console email in the server log
"""

import re
import sys
import uuid

import requests

sys.path.insert(0, "/home/dev-dir/PlateRoute/backend")
from tests import test_external as te  # noqa: E402

SERVER_LOG = "/tmp/dj_server.log"
API = "http://localhost:8000/api"
V1 = f"{API}/v1"

te.EMAIL = f"smoke-{uuid.uuid4().hex[:10]}@example.com"


def log(label, resp):
    te.log(label, resp)


# ---------------------------------------------------------------- public


def healthz():
    r = requests.get("http://localhost:8000/api/healthz/")
    log("Healthz", r)
    if r.status_code != 200:
        return False
    data = r.json()
    return data.get("db") is True and data.get("cache") is True


def openapi_schema():
    # drf-spectacular serves YAML by default; JSON requires an Accept header.
    r = requests.get(f"{API}/schema/", headers={"Accept": "application/json"})
    log("OpenAPI schema (json)", r)
    return r.status_code == 200 and r.json().get("openapi", "").startswith("3")


def discovery_public():
    r = requests.get(f"{V1}/restaurants/")
    log("Discovery (public list)", r)
    return r.status_code == 200


# ---------------------------------------------------------------- vendor onboarding

VENDOR_PAYLOAD = {
    "name": "Smoke Test Kitchen",
    "legal_name": "Smoke Test Kitchen Ltd",
    "trade_license_no": f"TL-{uuid.uuid4().hex[:8]}",
    "cuisines": ["bengali", "fastfood"],
}


def role_onboard_vendor():
    r = requests.post(f"{te.BASE}/role/", json={"role": "vendor"},
                      headers={"Authorization": f"Bearer {te.TOKEN}"})
    log("Role onboard (vendor)", r)
    return r.status_code == 200


def create_vendor():
    r = requests.post(f"{V1}/vendors/", json=VENDOR_PAYLOAD,
                      headers={"Authorization": f"Bearer {te.TOKEN}"})
    log("Create vendor", r)
    if r.status_code not in (200, 201):
        return False
    te.VENDOR_SLUG = r.json().get("slug")
    return bool(te.VENDOR_SLUG)


def create_branch():
    payload = {
        "vendor": te.VENDOR_SLUG,
        "name": "Smoke Branch 1",
        "lat": 23.8103,
        "lng": 90.4125,
        "address_text": "1 Test Road, Dhaka",
        "city": "Dhaka",
        "phone": "+8801700000000",
        "prep_minutes": 20,
        "min_order_minor": 10000,
        "currency": "BDT",
    }
    r = requests.post(f"{V1}/branches/", json=payload,
                      headers={"Authorization": f"Bearer {te.TOKEN}"})
    log("Create branch", r)
    if r.status_code not in (200, 201):
        return False
    te.BRANCH_UUID = r.json().get("uuid")
    return bool(te.BRANCH_UUID)


def submit_vendor():
    # By design, creating the first branch moves the vendor DRAFT -> PENDING
    # (vendors/serializers.py BranchSerializer.create), so a direct submit is
    # rejected with 409 "Only draft vendors can be submitted."
    r = requests.get(f"{V1}/vendors/{te.VENDOR_SLUG}/",
                     headers={"Authorization": f"Bearer {te.TOKEN}"})
    log("Get vendor (status after branch create)", r)
    ok = r.status_code == 200 and r.json().get("status") == "pending"
    r2 = requests.post(f"{V1}/vendors/{te.VENDOR_SLUG}/submit/", json={},
                       headers={"Authorization": f"Bearer {te.TOKEN}"})
    log("Resubmit pending vendor (expect 409)", r2)
    return ok and r2.status_code == 409


# ---------------------------------------------------------------- OTP reset via server log


def google_sso_post():
    # GoogleLoginView is POST-only: mobile clients send the Google ID token
    # (accounts/views.py). A bogus token must be rejected with 401.
    r = requests.post(f"{te.BASE}/google/login/", json={"id_token": "bogus.token.value"})
    log("Google SSO (bogus id_token, expect 401)", r)
    return r.status_code == 401


def request_password_reset_otp():
    r = requests.post(f"{te.BASE}/password-reset-otp/", json={"email": te.EMAIL})
    log("Password Reset OTP Request", r)
    if r.status_code != 200:
        return False
    txt = open(SERVER_LOG).read()
    codes = re.findall(r"password reset code is:\s*\n\s*\n\s*(\S{8})\n", txt)
    te.OTP_CODE = codes[-1] if codes else None
    print(f"  OTP parsed from console email log: {'yes' if te.OTP_CODE else 'NO'}")
    return True


def confirm_password_reset_otp():
    payload = {"email": te.EMAIL, "otp": te.OTP_CODE or "", "new_password": te.PASSWORD}
    r = requests.post(f"{te.BASE}/password-reset-otp/confirm/", json=payload)
    log("Password Reset OTP Confirm", r)
    if r.status_code != 200:
        return False
    r = requests.post(f"{te.BASE}/login/", json={"email": te.EMAIL, "password": te.PASSWORD})
    log("Login after password reset", r)
    return r.status_code == 200


tests = [
    ("Healthz (db + cache)", healthz),
    ("OpenAPI schema", openapi_schema),
    ("Discovery (public)", discovery_public),
    ("Register (email only)", te.register),
    ("Login (device1)", te.login),
    ("Save device1 token", te.save_device1_token),
    ("Profile (authorized)", te.profile),
    ("Profile (unauthorized)", te.profile_unauthorized),
    ("Role onboard (vendor)", role_onboard_vendor),
    ("Create vendor", create_vendor),
    ("Create branch", create_branch),
    ("Submit vendor + resubmit 409", submit_vendor),
    ("Token Refresh", te.token_refresh),
    ("Login (device2 - invalidates device1)", te.login_device2),
    ("Device1 token rejected", te.device1_token_invalid),
    ("Profile with device2 token", te.profile),
    ("Logout All Devices", te.logout_all),
    ("Profile (after logout)", te.profile_after_logout),
    ("Password Reset (request OTP)", request_password_reset_otp),
    ("Password Reset (confirm OTP + relogin)", confirm_password_reset_otp),
    ("Google SSO (rejects bogus id_token)", google_sso_post),
    ("Throttle Test", te.throttle_test),
]

if __name__ == "__main__":
    sys.exit(te.run(tests))
