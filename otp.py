"""Email One-Time Passcode (OTP) generation, hashing, rate-limiting & verification.

Backed by Google Cloud Firestore (collection ``portfolio_otp_codes``) when available,
with an automatic in-memory fallback for local development and unit tests.

Security properties:
- 6-digit numeric code generated via ``secrets.randbelow(1_000_000)`` (CSPRNG).
- Stored ONLY as an HMAC-SHA256 digest keyed with ``SESSION_SECRET`` + email salt.
- Expires after ``OTP_TTL_SECONDS`` (default 600s = 10 minutes).
- Single-use: consumed or invalidated immediately on success or after
  ``OTP_MAX_ATTEMPTS`` (default 5) failed verification attempts.
- Rate-limited per email (``OTP_MAX_SENDS_PER_WINDOW``, default 5 / 15 min) and
  per client IP (``OTP_MAX_IP_SENDS_PER_WINDOW``, default 20 / 15 min), plus a
  minimum resend cooldown (``OTP_RESEND_COOLDOWN_SECONDS``, default 30s).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

OTP_COLLECTION = os.environ.get("OTP_COLLECTION", "portfolio_otp_codes")
OTP_RATE_COLLECTION = os.environ.get("OTP_RATE_COLLECTION", "portfolio_otp_rate_limits")

OTP_TTL_SECONDS = int(os.environ.get("OTP_TTL_SECONDS", "600"))  # 10 minutes
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.environ.get("OTP_RESEND_COOLDOWN_SECONDS", "30"))
OTP_RATE_WINDOW_SECONDS = int(os.environ.get("OTP_RATE_WINDOW_SECONDS", "900"))  # 15 min
OTP_MAX_SENDS_PER_WINDOW = int(os.environ.get("OTP_MAX_SENDS_PER_WINDOW", "8"))
OTP_MAX_IP_SENDS_PER_WINDOW = int(os.environ.get("OTP_MAX_IP_SENDS_PER_WINDOW", "30"))

_MEM_CODES: dict[str, dict[str, Any]] = {}
_MEM_RATES: dict[str, list[float]] = {}

_FS_CLIENT = None
_FS_INIT_TRIED = False


def _get_firestore():
    """Return a lazily initialized Firestore client or None if unavailable."""
    global _FS_CLIENT, _FS_INIT_TRIED
    if _FS_INIT_TRIED:
        return _FS_CLIENT
    _FS_INIT_TRIED = True
    if os.environ.get("OTP_FORCE_MEMORY", "").strip().lower() in ("1", "true", "yes"):
        return None
    try:
        from google.cloud import firestore  # type: ignore

        project = (
            os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCP_PROJECT")
            or None
        )
        _FS_CLIENT = firestore.Client(project=project)
        return _FS_CLIENT
    except Exception as exc:
        logger.warning("Firestore unavailable for OTP store (%s); using in-memory store.", exc)
        _FS_CLIENT = None
        return None


def _hmac_key() -> bytes:
    secret = (
        os.environ.get("SESSION_SECRET")
        or os.environ.get("OTP_SECRET")
        or "Y0A-WWfWSWDYw9MsZAmUihlgOoN7SG2Jr5tX-wtgXxSgeqbe9KhtQOvn1SYQ396u"
    )
    return secret.encode("utf-8")


def hash_otp(email: str, code: str) -> str:
    """Compute HMAC-SHA256 digest of (email, code)."""
    msg = f"{email.strip().lower()}:{code.strip()}".encode("utf-8")
    return hmac.new(_hmac_key(), msg, hashlib.sha256).hexdigest()


def generate_otp_code() -> str:
    """Return a cryptographically random 6-digit numeric string ('000000'..'999999')."""
    return f"{secrets.randbelow(1_000_000):06d}"


class OTPRateLimitError(Exception):
    """Raised when an email or IP exceeds the OTP send rate limit."""

    def __init__(self, message: str, retry_after_seconds: int = 30):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _load_code_record(email_key: str) -> Optional[dict[str, Any]]:
    db = _get_firestore()
    if db is not None:
        try:
            snap = db.collection(OTP_COLLECTION).document(email_key).get()
            if snap.exists:
                return snap.to_dict()
        except Exception as exc:
            logger.warning("Firestore OTP read failed (%s); falling back to memory.", exc)
    return _MEM_CODES.get(email_key)


def _save_code_record(email_key: str, record: dict[str, Any]) -> None:
    _MEM_CODES[email_key] = dict(record)
    db = _get_firestore()
    if db is not None:
        try:
            db.collection(OTP_COLLECTION).document(email_key).set(record)
        except Exception as exc:
            logger.warning("Firestore OTP write failed (%s); kept in memory.", exc)


def _delete_code_record(email_key: str) -> None:
    _MEM_CODES.pop(email_key, None)
    db = _get_firestore()
    if db is not None:
        try:
            db.collection(OTP_COLLECTION).document(email_key).delete()
        except Exception as exc:
            logger.warning("Firestore OTP delete failed (%s).", exc)


def _check_and_record_rate(bucket_key: str, max_events: int, window_seconds: int) -> None:
    now = time.time()
    cutoff = now - window_seconds
    events = [t for t in _MEM_RATES.get(bucket_key, []) if t > cutoff]

    db = _get_firestore()
    if db is not None:
        try:
            doc_ref = db.collection(OTP_RATE_COLLECTION).document(bucket_key)
            snap = doc_ref.get()
            if snap.exists:
                data = snap.to_dict() or {}
                fs_events = [float(t) for t in data.get("events", []) if float(t) > cutoff]
                if len(fs_events) > len(events):
                    events = fs_events
        except Exception as exc:
            logger.warning("Firestore OTP rate read failed (%s).", exc)

    if len(events) >= max_events:
        oldest = min(events)
        retry_after = max(1, int(oldest + window_seconds - now))
        raise OTPRateLimitError(
            f"Too many sign-in codes requested. Please wait {retry_after}s before trying again.",
            retry_after_seconds=retry_after,
        )

    events.append(now)
    _MEM_RATES[bucket_key] = events
    if db is not None:
        try:
            db.collection(OTP_RATE_COLLECTION).document(bucket_key).set(
                {"events": events, "updated_at": now}
            )
        except Exception as exc:
            logger.warning("Firestore OTP rate write failed (%s).", exc)


def issue_otp(
    email: str,
    client_ip: str = "",
    name: str = "",
    company: str = "",
    role: str = "",
) -> tuple[str, int]:
    """Generate, store, and return ``(code, ttl_seconds)`` for ``email``.

    Enforces cooldown + per-email + per-IP rate limits.
    """
    email_key = email.strip().lower()
    now = time.time()

    existing = _load_code_record(email_key)
    if existing:
        issued_at = float(existing.get("issued_at", 0))
        elapsed = now - issued_at
        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            wait_s = max(1, int(OTP_RESEND_COOLDOWN_SECONDS - elapsed))
            raise OTPRateLimitError(
                f"A code was just sent. Please wait {wait_s}s before requesting another.",
                retry_after_seconds=wait_s,
            )

    _check_and_record_rate(
        f"email:{hashlib.sha256(email_key.encode()).hexdigest()[:32]}",
        OTP_MAX_SENDS_PER_WINDOW,
        OTP_RATE_WINDOW_SECONDS,
    )
    if client_ip:
        _check_and_record_rate(
            f"ip:{hashlib.sha256(client_ip.encode()).hexdigest()[:32]}",
            OTP_MAX_IP_SENDS_PER_WINDOW,
            OTP_RATE_WINDOW_SECONDS,
        )

    code = generate_otp_code()
    record = {
        "email": email_key,
        "name": name.strip(),
        "company": company.strip(),
        "role": role.strip(),
        "code_hash": hash_otp(email_key, code),
        "issued_at": now,
        "expires_at": now + OTP_TTL_SECONDS,
        "attempts": 0,
        "consumed": False,
        "client_ip": client_ip,
    }
    _save_code_record(email_key, record)
    return code, OTP_TTL_SECONDS


def verify_otp(email: str, code: str) -> tuple[bool, str, dict[str, str]]:
    """Verify ``code`` for ``email``.

    Returns ``(ok, reason, metadata)`` where metadata includes captured name/company/role.
    """
    email_key = (email or "").strip().lower()
    clean_code = "".join(ch for ch in (code or "") if ch.isdigit())
    if not email_key or len(clean_code) != 6:
        return False, "Please enter the 6-digit verification code sent to your work email.", {}

    record = _load_code_record(email_key)
    if not record or record.get("consumed"):
        return False, "No active verification code found. Please request a new code.", {}

    now = time.time()
    if now > float(record.get("expires_at", 0)):
        _delete_code_record(email_key)
        return False, "This verification code has expired. Please request a new code.", {}

    attempts = int(record.get("attempts", 0))
    if attempts >= OTP_MAX_ATTEMPTS:
        _delete_code_record(email_key)
        return False, "Too many incorrect attempts. Please request a new verification code.", {}

    expected_hash = str(record.get("code_hash", ""))
    actual_hash = hash_otp(email_key, clean_code)

    if not hmac.compare_digest(expected_hash, actual_hash):
        attempts += 1
        if attempts >= OTP_MAX_ATTEMPTS:
            _delete_code_record(email_key)
            return False, "Too many incorrect attempts. Please request a new verification code.", {}
        record["attempts"] = attempts
        _save_code_record(email_key, record)
        remaining = OTP_MAX_ATTEMPTS - attempts
        return (
            False,
            f"Incorrect code. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
            {},
        )

    metadata = {
        "name": str(record.get("name") or "").strip(),
        "company": str(record.get("company") or "").strip(),
        "role": str(record.get("role") or "").strip(),
    }
    _delete_code_record(email_key)
    return True, "ok", metadata


def reset_memory_stores_for_tests() -> None:
    """Clear in-memory OTP and rate-limit stores (used by test suites)."""
    _MEM_CODES.clear()
    _MEM_RATES.clear()
