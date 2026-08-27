"""Password-reset OTP generation and hashing helpers.

Codes are 8 characters long and always contain at least one digit, one
letter and one special character, as required.
"""

import hashlib
import secrets

# Required OTP length.
OTP_LENGTH = 8

# Alphabets deliberately exclude visually ambiguous characters (0/O/o,
# 1/I/l) and characters that are awkward to read or retype from an email
# (quotes, backslash, backtick, whitespace).
OTP_DIGITS = "23456789"
OTP_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
OTP_LOWER = "abcdefghijkmnpqrstuvwxyz"
OTP_SPECIALS = "!@#$%^&*-_=+"

ALL_OTP_CHARS = OTP_DIGITS + OTP_UPPER + OTP_LOWER + OTP_SPECIALS


def generate_otp(length=OTP_LENGTH):
    """Return a cryptographically secure OTP of ``length`` characters.

    One character is picked from each category (digit, letter, special) so
    the requested mix is guaranteed without fragile rejection sampling;
    remaining positions come from the combined alphabet. Positions are then
    securely shuffled so category placement does not leak.
    """
    if length < 3:
        raise ValueError("OTP length must be at least 3 to cover all categories.")

    rng = secrets.SystemRandom()
    chars = [
        rng.choice(OTP_DIGITS),
        rng.choice(OTP_UPPER + OTP_LOWER),
        rng.choice(OTP_SPECIALS),
    ]
    chars.extend(rng.choice(ALL_OTP_CHARS) for _ in range(length - len(chars)))
    rng.shuffle(chars)
    return "".join(chars)


def normalize_otp(raw):
    """Normalize user-supplied input before hashing/comparison.

    Verification is case-insensitive and ignores surrounding whitespace so
    users do not fail because of caps-lock or copy/paste artifacts.
    """
    return (raw or "").strip().lower()


def hash_otp(raw):
    """Return the SHA-256 hex digest of a raw OTP for storage/lookup.

    Only this hash is ever persisted, so database leakage cannot reveal
    usable codes.
    """
    return hashlib.sha256(normalize_otp(raw).encode("utf-8")).hexdigest()
