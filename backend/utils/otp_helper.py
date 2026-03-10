# =============================================================================
# utils/otp_helper.py
# Shared OTP utilities used by register, forgot-password, forgot-username flows
# =============================================================================

import random
import time
import secrets
import urllib.request
import json

# ── In-memory stores (reset on server restart) ────────────────────────────────
# For production, replace these with Redis or a DB table.
_otp_store   = {}   # key  → { otp, expires_at, ...extra fields }
_token_store = {}   # reset_token → { mobile, expires_at }

# ── Fast2SMS API key ──────────────────────────────────────────────────────────
# Get a free key at https://fast2sms.com → Dev API
# Paste your key below:
FAST2SMS_KEY = "fV9zBZdprNoHDvYjxlMLhRSyWPA4gqc0uk3wETa1isFX2t7bGUDSRJnM4ce2tVbdo6WPaTOxliK3zmXp"


def make_otp() -> str:
    """Generate a random 6-digit OTP string."""
    return str(random.randint(100000, 999999))


def send_sms(mobile: str, otp: str) -> tuple[bool, str | None]:
    """
    Send an OTP via Fast2SMS.
    Returns (True, None) on success, (False, error_message) on failure.
    """
    payload = json.dumps({
        "route": "otp",
        "variables_values": str(otp),
        "numbers": mobile,
        "flash": 0
    }).encode()

    req = urllib.request.Request(
        "https://www.fast2sms.com/dev/bulkV2",
        data=payload,
        method="POST"
    )
    req.add_header("authorization", FAST2SMS_KEY)
    req.add_header("Content-Type",  "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            r = json.loads(resp.read())
            if r.get("return") is True:
                return True, None
            return False, r.get("message", "SMS failed")
    except Exception as e:
        return False, str(e)


def store_otp(key: str, otp: str, ttl_seconds: int = 600, **extra):
    """
    Save an OTP in the in-memory store.
    key        — unique string (e.g. 'reg_9876543210')
    ttl_seconds — how long before the OTP expires (default 10 min)
    **extra    — any additional fields to save alongside (username, password…)
    """
    _otp_store[key] = {
        "otp":        otp,
        "expires_at": time.time() + ttl_seconds,
        **extra
    }


def verify_otp(key: str, otp: str) -> tuple[bool, str | None, dict | None]:
    """
    Check an OTP against the store.
    Returns (True, None, stored_data) on success.
    Returns (False, error_message, None) on failure.
    """
    stored = _otp_store.get(key)
    if not stored:
        return False, "OTP expired or not sent. Request a new OTP.", None
    if time.time() > stored["expires_at"]:
        del _otp_store[key]
        return False, "OTP has expired. Please request a new one.", None
    if stored["otp"] != otp:
        return False, "Incorrect OTP. Please try again.", None
    return True, None, stored


def consume_otp(key: str):
    """Delete an OTP from the store after successful use."""
    _otp_store.pop(key, None)


def issue_reset_token(mobile: str, ttl_seconds: int = 300) -> str:
    """
    Issue a one-time password-reset token valid for ttl_seconds (default 5 min).
    Returns the token string.
    """
    token = secrets.token_urlsafe(32)
    _token_store[token] = {
        "mobile":     mobile,
        "expires_at": time.time() + ttl_seconds
    }
    return token


def verify_reset_token(token: str) -> tuple[bool, str | None, str | None]:
    """
    Validate a reset token.
    Returns (True, None, mobile) on success.
    Returns (False, error_message, None) on failure.
    """
    stored = _token_store.get(token)
    if not stored:
        return False, "Invalid or expired session. Please start over.", None
    if time.time() > stored["expires_at"]:
        del _token_store[token]
        return False, "Session expired. Please start over.", None
    return True, None, stored["mobile"]


def consume_reset_token(token: str):
    """Delete a reset token after successful use."""
    _token_store.pop(token, None)