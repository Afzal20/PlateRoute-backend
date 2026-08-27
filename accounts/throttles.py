from rest_framework.throttling import AnonRateThrottle


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class RegisterThrottle(AnonRateThrottle):
    scope = "register"


class PasswordResetRequestThrottle(AnonRateThrottle):
    """Limits OTP issuance per IP to prevent email bombing."""

    scope = "password_reset_request"


class PasswordResetConfirmThrottle(AnonRateThrottle):
    """Slows brute-force guessing of codes during confirmation."""

    scope = "password_reset_confirm"
