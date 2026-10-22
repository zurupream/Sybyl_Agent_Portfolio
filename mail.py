"""Outbound email delivery for 6-digit passwordless sign-in codes (OTP).

Uses Google Workspace SMTP (``smtp.gmail.com:587`` STARTTLS) with credentials
supplied via environment variables / Google Secret Manager:
- ``SMTP_HOST`` (default ``smtp.gmail.com``)
- ``SMTP_PORT`` (default ``587``)
- ``SMTP_USER`` (default ``psrmreports@sybyl.com``)
- ``SMTP_PASSWORD`` (Google Workspace App Password stored in Secret Manager)
- ``OTP_FROM_ADDRESS`` (default ``psrmreports@sybyl.com``)
- ``OTP_FROM_NAME`` (default ``Sybyl Enterprise AI Portfolio``)

When ``OTP_TEST_MODE=1`` is set (used by automated test suites), emails are
recorded into an in-memory outbox instead of opening an external SMTP socket.
"""

from __future__ import annotations

from email.message import EmailMessage
import logging
import os
import smtplib
import ssl
from typing import Any

logger = logging.getLogger(__name__)

_TEST_OUTBOX: list[dict[str, Any]] = []


def get_test_outbox() -> list[dict[str, Any]]:
    """Return captured emails when ``OTP_TEST_MODE=1`` is enabled."""
    return _TEST_OUTBOX


def clear_test_outbox() -> None:
    """Clear captured test emails."""
    _TEST_OUTBOX.clear()


def send_otp_email(to_email: str, code: str, ttl_seconds: int = 600, recipient_name: str = "") -> None:
    """Send a 6-digit sign-in verification code to ``to_email``."""
    from_addr = os.environ.get("OTP_FROM_ADDRESS") or os.environ.get("SMTP_USER") or "psrmreports@sybyl.com"
    from_name = os.environ.get("OTP_FROM_NAME", "Sybyl Enterprise AI Portfolio")
    ttl_minutes = max(1, ttl_seconds // 60)
    greeting = f"Hello {recipient_name.strip()}," if recipient_name and recipient_name.strip() else "Hello,"

    subject = f"{code} is your Sybyl AI Portfolio sign-in code"

    text_body = (
        f"Sybyl Enterprise AI Portfolio — Single Sign-On Verification\n\n"
        f"{greeting}\n\n"
        f"Your one-time verification code to access all 61 Enterprise AI Agents is:\n\n"
        f"    {code}\n\n"
        f"This code expires in {ttl_minutes} minutes and can only be used once.\n"
        f"If you did not request this code, you can safely ignore this email.\n\n"
        f"— Sybyl Enterprise AI Team\n"
    )

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<body style="margin:0;padding:24px;background-color:#F5F5F7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1D1D1F;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;margin:0 auto;background:#FFFFFF;border-radius:16px;border:1px solid #E5E5EA;padding:32px;">
    <tr>
      <td>
        <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#0071E3;margin-bottom:8px;">
          Sybyl Enterprise AI Portfolio · 61 Live Agents
        </div>
        <h1 style="font-size:22px;font-weight:700;margin:0 0 12px 0;color:#1D1D1F;">
          Your single sign-on verification code
        </h1>
        <p style="font-size:15px;line-height:1.5;color:#515154;margin:0 0 24px 0;">
          {greeting} enter the 6-digit code below in your browser to unlock instant access to all 61 Enterprise AI Agents across 8 sectors:
        </p>
        <div style="background:#F5F5F7;border:1px solid #D2D2D7;border-radius:12px;padding:20px;text-align:center;margin:0 0 24px 0;">
          <span style="font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;font-size:34px;font-weight:700;letter-spacing:10px;color:#1D1D1F;">
            {code}
          </span>
        </div>
        <p style="font-size:13px;line-height:1.5;color:#86868B;margin:0;">
          This code expires in <strong>{ttl_minutes} minutes</strong> and is valid for a single sign-in.
          If you did not request this email, no action is required.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""

    if os.environ.get("OTP_TEST_MODE", "").strip().lower() in ("1", "true", "yes"):
        _TEST_OUTBOX.append(
            {
                "to": to_email,
                "from": from_addr,
                "subject": subject,
                "code": code,
                "name": recipient_name,
                "text": text_body,
                "html": html_body,
            }
        )
        logger.info("OTP_TEST_MODE active: captured OTP for %s in memory outbox.", to_email)
        return

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", from_addr).strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()
    use_tls = os.environ.get("SMTP_USE_TLS", "1").strip().lower() not in ("0", "false", "no")

    if not smtp_password:
        raise RuntimeError(
            "SMTP_PASSWORD is not configured. Set SMTP_PASSWORD (or enable OTP_TEST_MODE=1 in tests)."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        server.ehlo()
        if use_tls:
            server.starttls(context=context)
            server.ehlo()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
    logger.info("Dispatched OTP verification email to %s via %s:%s", to_email, smtp_host, smtp_port)
