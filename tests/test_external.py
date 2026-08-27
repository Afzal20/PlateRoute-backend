import requests
import sys

BASE = "http://localhost:8000/api/auth"
EMAIL = "afzalhossen2019@gmail.com"
PASSWORD = "AfzalTest123!"
TOKEN = None
REFRESH = None
DEVICE1_TOKEN = None


def log(label, resp):
    print(f"[{resp.status_code}] {label}")
    if resp.status_code >= 400:
        print(f"  {resp.text[:200]}")


def register():
    r = requests.post(f"{BASE}/register/", json={"email": EMAIL, "password": PASSWORD})
    log("Register", r)
    return r.status_code == 201


def login():
    global TOKEN, REFRESH
    r = requests.post(f"{BASE}/login/", json={"email": EMAIL, "password": PASSWORD})
    log("Login", r)
    if r.status_code == 200:
        data = r.json()
        TOKEN = data.get("access")
        REFRESH = data.get("refresh")
        return True
    return False


def save_device1_token():
    global DEVICE1_TOKEN
    DEVICE1_TOKEN = TOKEN
    log("Saved device1 token", type("R", (), {"status_code": 0})())
    print(f"  Token: {DEVICE1_TOKEN[:30]}...")
    return True


def login_device2():
    global TOKEN, REFRESH
    r = requests.post(f"{BASE}/login/", json={"email": EMAIL, "password": PASSWORD})
    log("Login (device2)", r)
    if r.status_code == 200:
        TOKEN = r.json().get("access")
        REFRESH = r.json().get("refresh")
        return True
    return False


def device1_token_invalid():
    r = requests.get(f"{BASE}/profile/", headers={"Authorization": f"Bearer {DEVICE1_TOKEN}"})
    log("Device1 token after device2 login", r)
    return r.status_code == 401


def profile():
    r = requests.get(f"{BASE}/profile/", headers={"Authorization": f"Bearer {TOKEN}"})
    log("Profile (GET)", r)
    if r.status_code == 200:
        print(f"  {r.json()}")
    return r.status_code == 200


def profile_update():
    global EMAIL
    r = requests.patch(
        f"{BASE}/profile/",
        json={"email": "updated@gmail.com"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    log("Profile (PATCH)", r)
    if r.status_code == 200:
        EMAIL = "updated@gmail.com"
    return r.status_code == 200


def profile_unauthorized():
    r = requests.get(f"{BASE}/profile/")
    log("Profile (no token)", r)
    return r.status_code == 401


def logout_all():
    r = requests.post(f"{BASE}/logout/", headers={"Authorization": f"Bearer {TOKEN}"})
    log("Logout All", r)
    return r.status_code == 200


def profile_after_logout():
    r = requests.get(f"{BASE}/profile/", headers={"Authorization": f"Bearer {TOKEN}"})
    log("Profile (after logout)", r)
    return r.status_code == 401


def token_refresh():
    global TOKEN
    r = requests.post(f"{BASE}/token/refresh/", json={"refresh": REFRESH})
    log("Token Refresh", r)
    if r.status_code == 200:
        TOKEN = r.json().get("access")
        return True
    return False


def password_reset():
    r = requests.post(f"{BASE}/password-reset/", json={"email": EMAIL})
    log("Password Reset", r)
    return r.status_code == 200


def google_sso_redirect():
    r = requests.get(f"{BASE}/google/login/", allow_redirects=False)
    log("Google SSO Redirect", r)
    is_google = "accounts.google.com" in r.headers.get("Location", "")
    return r.status_code in (301, 302) and is_google


def throttle_test():
    print("\n--- Throttle test (6 rapid failed logins) ---")
    for i in range(6):
        r = requests.post(f"{BASE}/login/", json={"email": EMAIL, "password": "wrong"})
        s = "BLOCKED" if r.status_code == 429 else "OK"
        print(f"  Attempt {i+1}: [{r.status_code}] {s}")
    return True


def run(tests):
    results = []
    for name, fn in tests:
        print(f"\n--- {name} ---")
        try:
            ok = fn()
        except Exception as e:
            print(f"  ERROR: {e}")
            ok = False
        results.append((name, ok))

    print("\n" + "=" * 40)
    print("RESULTS:")
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'} {name}")
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    tests = [
        ("Register (email only)", register),
        ("Login (device1)", login),
        ("Save device1 token", save_device1_token),
        ("Profile (authorized)", profile),
        ("Profile Update", profile_update),
        ("Profile (unauthorized)", profile_unauthorized),
        ("Token Refresh", token_refresh),
        ("Login (device2 - invalidates device1)", login_device2),
        ("Device1 token rejected", device1_token_invalid),
        ("Profile with device2 token", profile),
        ("Login again", login),
        ("Logout All Devices", logout_all),
        ("Profile (after logout)", profile_after_logout),
        ("Password Reset", password_reset),
        ("Google SSO Redirect", google_sso_redirect),
        ("Throttle Test", throttle_test),
    ]

    sys.exit(run(tests))
