"""Enterprise Single Sign-On & Lead-Capture Gateway for Sybyl Agentic AI Portfolio.

Inspired directly by the Bank Statement Analyzer authentication gateway:
1. Primary Action (External Prospects & Partners — Lead Generation):
   Passwordless 6-digit OTP sign-in via Work Email, capturing Full Name,
   Company / Organisation, Job Title / Role, and Work Email while blocking
   consumer/personal domains (gmail.com, yahoo.com, outlook.com, etc.) and
   disposable domains.
2. Secondary Action (Sybyl Staff):
   Google Workspace Single Sign-In (@sybyl.com and ALLOWED_EMAILS).
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from typing import Any, Optional

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from itsdangerous import TimestampSigner

DEFAULT_OAUTH_CLIENT_ID = (
    "259388273008-n8vg3ae8be86e56svvg09rbdciah17u1.apps.googleusercontent.com"
)
DEFAULT_SESSION_SECRET = (
    "Y0A-WWfWSWDYw9MsZAmUihlgOoN7SG2Jr5tX-wtgXxSgeqbe9KhtQOvn1SYQ396u"
)
SESSION_MAX_AGE_SECONDS = 60 * 60 * 8  # 8 hours

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@([A-Za-z0-9\-]+\.)+[A-Za-z]{2,24}$")

BLOCKED_CONSUMER_DOMAINS: frozenset[str] = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.co.uk",
        "yahoo.co.in",
        "yahoo.fr",
        "yahoo.de",
        "yahoo.ca",
        "ymail.com",
        "rocketmail.com",
        "outlook.com",
        "hotmail.com",
        "hotmail.co.uk",
        "hotmail.fr",
        "live.com",
        "live.co.uk",
        "msn.com",
        "Passport.com",
        "icloud.com",
        "me.com",
        "mac.com",
        "aol.com",
        "aim.com",
        "protonmail.com",
        "proton.me",
        "pm.me",
        "zoho.com",
        "zohomail.com",
        "gmx.com",
        "gmx.de",
        "gmx.net",
        "mail.com",
        "email.com",
        "usa.com",
        "yandex.com",
        "yandex.ru",
        "mail.ru",
        "bk.ru",
        "inbox.ru",
        "list.ru",
        "qq.com",
        "163.com",
        "126.com",
        "sina.com",
        "rediffmail.com",
        "fastmail.com",
        "fastmail.fm",
        "tutanota.com",
        "tuta.io",
        "tuta.com",
        "hey.com",
        "comcast.net",
        "verizon.net",
        "att.net",
        "sbcglobal.net",
        "bellsouth.net",
        "cox.net",
        "charter.net",
        "earthlink.net",
        "optonline.net",
        "btinternet.com",
        "virginmedia.com",
        "sky.com",
        "talktalk.net",
        "orange.fr",
        "wanadoo.fr",
        "free.fr",
        "laposte.net",
        "sfr.fr",
        "web.de",
        "t-online.de",
        "freenet.de",
        "libero.it",
        "virgilio.it",
        "tin.it",
        "alice.it",
        "terra.com.br",
        "uol.com.br",
        "bol.com.br",
        "ig.com.br",
        "globo.com",
        "naver.com",
        "daum.net",
        "hanmail.net",
    }
)

BLOCKED_DISPOSABLE_DOMAINS: frozenset[str] = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "guerrillamailblock.com",
        "sharklasers.com",
        "grr.la",
        "pokemail.net",
        "spam4.me",
        "10minutemail.com",
        "10minutemail.net",
        "tempmail.com",
        "temp-mail.org",
        "temp-mail.io",
        "throwawaymail.com",
        "yopmail.com",
        "yopmail.fr",
        "yopmail.net",
        "getnada.com",
        "nada.email",
        "maildrop.cc",
        "trashmail.com",
        "trashmail.net",
        "dispostable.com",
        "fakeinbox.com",
        "mailnesia.com",
        "mailcatch.com",
        "mintemail.com",
        "mohmal.com",
        "harakirimail.com",
        "jetable.org",
        "mytemp.email",
        "BurnerMail.io",
        "burnermail.io",
        "guerrillamail.net",
        "guerrillamail.org",
        "guerrillamail.biz",
        "guerrillamail.de",
        "mailnull.com",
        "incognitomail.com",
        "spamgourmet.com",
        "tempmailaddress.com",
        "crazymailing.com",
        "discard.email",
        "discardmail.com",
        " emailsensei.com",
        "emailondeck.com",
    }
)


def get_oauth_client_id() -> str:
    return (
        os.environ.get("OAUTH_CLIENT_ID", "").strip()
        or os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
        or DEFAULT_OAUTH_CLIENT_ID
    )


def get_session_secret() -> str:
    return os.environ.get("SESSION_SECRET", "").strip() or DEFAULT_SESSION_SECRET


def get_allowed_domains() -> list[str]:
    raw = os.environ.get("ALLOWED_DOMAINS", "sybyl.com,kimisitusacco.or.ke")
    return [d.strip().lower() for d in raw.split(",") if d.strip()]


def get_allowed_emails() -> list[str]:
    raw = os.environ.get(
        "ALLOWED_EMAILS",
        "zuruprem@gmail.com,guruprem.saginadham@sybyl.com",
    )
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


def get_admin_emails() -> list[str]:
    raw = os.environ.get(
        "ADMIN_EMAILS",
        "guruprem.saginadham@sybyl.com,zuruprem@gmail.com",
    )
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


def is_open_business_signup() -> bool:
    val = os.environ.get("OPEN_BUSINESS_SIGNUP", "1").strip().lower()
    return val not in ("0", "false", "no")


def is_admin_user(email: str) -> bool:
    clean = (email or "").strip().lower()
    if not clean:
        return False
    if clean in get_admin_emails():
        return True
    domain = clean.split("@")[-1] if "@" in clean else ""
    return domain == "sybyl.com"


def check_work_email_allowed(email: str) -> tuple[bool, str]:
    """Validate whether ``email`` is allowed for Passwordless Work Email Sign-In.

    1. Validates RFC-style syntax.
    2. Explicit ``ALLOWED_EMAILS`` always pass.
    3. Blocks consumer/personal domains (gmail.com, yahoo.com, outlook.com, etc.)
       and disposable domains.
    4. Allows explicit ``ALLOWED_DOMAINS`` or any valid corporate domain when
       ``OPEN_BUSINESS_SIGNUP=1``.
    """
    clean = (email or "").strip().lower()
    if not clean or not EMAIL_REGEX.match(clean):
        return False, "Please enter a valid work email address (for example, name@company.com)."

    if clean in get_allowed_emails():
        return True, "ok"

    domain = clean.split("@", 1)[1].strip().lower()

    if domain in BLOCKED_DISPOSABLE_DOMAINS:
        return (
            False,
            f"Temporary or disposable email addresses (@{domain}) are not permitted. "
            "Please sign in with your company work email.",
        )

    if domain in BLOCKED_CONSUMER_DOMAINS:
        return (
            False,
            f"Personal email addresses (@{domain}) are not permitted for free portfolio access. "
            "Please use your corporate or institutional work email (e.g. name@yourcompany.com).",
        )

    allowed_domains = get_allowed_domains()
    if domain in allowed_domains:
        return True, "ok"

    if is_open_business_signup():
        return True, "ok"

    return (
        False,
        f"Your domain (@{domain}) is not yet enabled. Please contact Sybyl to request access.",
    )


def check_google_staff_allowed(email: str, hd: Optional[str] = None) -> tuple[bool, str]:
    """Validate whether a Google Sign-In account is authorized (Sybyl staff or explicit allowlist)."""
    clean = (email or "").strip().lower()
    if not clean or "@" not in clean:
        return False, "Google account did not return a valid email address."

    if clean in get_allowed_emails() or clean in get_admin_emails():
        return True, "ok"

    domain = clean.split("@", 1)[1].strip().lower()
    allowed_domains = get_allowed_domains()
    if domain in allowed_domains or (hd and hd.strip().lower() in allowed_domains):
        return True, "ok"

    return (
        False,
        f"Google Sign-In is reserved for Sybyl staff (@sybyl.com). "
        f"External guests ({clean}) can sign in right above using our free Passwordless Work Email option.",
    )


def verify_google_credential(token: str) -> dict[str, Any]:
    """Verify a Google ID token JWT and enforce Sybyl staff / allowlist policy."""
    client_id = get_oauth_client_id()
    if not client_id:
        raise PermissionError("OAUTH_CLIENT_ID is not configured on the server.")

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
        )
    except Exception as exc:
        raise ValueError(f"Invalid Google ID token: {exc}") from exc

    if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError("Invalid token issuer.")

    if not idinfo.get("email_verified", False):
        raise PermissionError("Google account email is not verified.")

    email = (idinfo.get("email") or "").lower().strip()
    hd = idinfo.get("hd")
    allowed, reason = check_google_staff_allowed(email, hd)
    if not allowed:
        raise PermissionError(reason)

    now = int(time.time())
    return {
        "email": email,
        "name": idinfo.get("name") or email.split("@")[0].replace(".", " ").title(),
        "company": "Sybyl" if email.endswith("@sybyl.com") else hd or "Sybyl Partner",
        "role": "Sybyl Staff",
        "picture": idinfo.get("picture") or "",
        "hd": hd or email.split("@")[-1],
        "sub": idinfo.get("sub") or "",
        "provider": "google",
        "iat": now,
        "exp": now + SESSION_MAX_AGE_SECONDS,
    }


def create_starlette_session_cookie_value(session_data: dict[str, Any]) -> str:
    """Create a Starlette SessionMiddleware-compatible signed cookie string.

    This allows upstream Starlette apps sharing SESSION_SECRET (such as
    bank-statement-agent) to immediately accept the authenticated session.
    """
    payload = base64.b64encode(json.dumps(session_data).encode("utf-8"))
    signer = TimestampSigner(get_session_secret())
    return signer.sign(payload).decode("utf-8")


LOGIN_PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Sign In — Sybyl Enterprise AI Portfolio (61 Live Agents)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">
<script src="https://accounts.google.com/gsi/client" async defer></script>
<style>
  :root {
    --bg: #F5F5F7;
    --surface: #FFFFFF;
    --ink: #1D1D1F;
    --ink-secondary: #515154;
    --muted: #86868B;
    --line: #E5E5EA;
    --line-strong: #D2D2D7;
    --accent: #0071E3;
    --accent-hover: #0077ED;
    --accent-soft: rgba(0, 113, 227, 0.08);
    --success: #1D7D3F;
    --success-soft: #E8F5EC;
    --danger: #C93400;
    --danger-soft: #FFF2EE;
    --hero-bg-1: #0B101E;
    --hero-bg-2: #131D38;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    min-height: 100vh;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif;
    background: var(--bg);
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
  }
  .split-layout {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    min-height: 100vh;
  }
  /* Left Hero Column */
  .hero-pane {
    background: radial-gradient(circle at 18% 18%, rgba(0, 113, 227, 0.25), transparent 48%),
                radial-gradient(circle at 85% 82%, rgba(94, 92, 230, 0.22), transparent 50%),
                linear-gradient(145deg, var(--hero-bg-1) 0%, var(--hero-bg-2) 100%);
    color: #FFFFFF;
    padding: 44px 52px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
  }
  .brand-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .brand-logo-wrap {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .brand-mark {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: linear-gradient(135deg, #0071E3 0%, #47A1FF 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 19px;
    color: #FFFFFF;
    box-shadow: 0 8px 20px rgba(0, 113, 227, 0.38);
  }
  .brand-name {
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #FFFFFF;
  }
  .brand-sub {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.65);
    font-weight: 500;
  }
  .eyebrow-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.09);
    border: 1px solid rgba(255, 255, 255, 0.16);
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #7CC0FF;
    margin-bottom: 18px;
  }
  .eyebrow-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #30D158;
    box-shadow: 0 0 8px #30D158;
  }
  .hero-main {
    margin: auto 0;
    padding: 20px 0;
    max-width: 640px;
  }
  .hero-title {
    font-size: clamp(28px, 3vw, 40px);
    font-weight: 800;
    line-height: 1.12;
    letter-spacing: -0.03em;
    margin-bottom: 14px;
    color: #FFFFFF;
  }
  .hero-subtitle {
    font-size: 15.5px;
    line-height: 1.58;
    color: rgba(255, 255, 255, 0.78);
    margin-bottom: 28px;
  }
  .workflow-box {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
    padding: 22px 24px;
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
  }
  .workflow-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(255, 255, 255, 0.55);
    margin-bottom: 14px;
  }
  .workflow-steps {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .wf-step {
    display: flex;
    align-items: flex-start;
    gap: 14px;
  }
  .wf-num {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: rgba(0, 113, 227, 0.28);
    border: 1px solid rgba(124, 192, 255, 0.4);
    color: #7CC0FF;
    font-weight: 700;
    font-size: 13px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
  }
  .wf-title {
    font-size: 14px;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 2px;
  }
  .wf-desc {
    font-size: 12.8px;
    line-height: 1.45;
    color: rgba(255, 255, 255, 0.7);
  }
  .sector-pills-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .sector-pill {
    font-size: 11.5px;
    font-weight: 600;
    padding: 6px 11px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.13);
    color: rgba(255, 255, 255, 0.88);
  }
  .sector-pill strong {
    color: #7CC0FF;
    margin-left: 3px;
  }
  .hero-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    padding-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 12px;
    color: rgba(255, 255, 255, 0.58);
  }
  .trust-badges {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
  }
  .trust-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  /* Right Auth Column */
  .auth-pane {
    background: var(--bg);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 36px 28px;
  }
  .auth-card {
    width: 100%;
    max-width: 460px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 22px;
    padding: 36px 34px;
    box-shadow: 0 18px 45px rgba(0, 0, 0, 0.06);
  }
  .auth-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--accent);
    background: var(--accent-soft);
    padding: 5px 11px;
    border-radius: 999px;
    margin-bottom: 12px;
  }
  .auth-title {
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.025em;
    color: var(--ink);
    margin-bottom: 6px;
  }
  .auth-subtitle {
    font-size: 13.8px;
    line-height: 1.5;
    color: var(--ink-secondary);
    margin-bottom: 22px;
  }
  .form-grid {
    display: flex;
    flex-direction: column;
    gap: 13px;
  }
  .form-row-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .field-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .field-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .field-hint {
    font-size: 11px;
    font-weight: 500;
    color: var(--muted);
  }
  .text-input {
    width: 100%;
    height: 42px;
    padding: 0 13px;
    border-radius: 10px;
    border: 1px solid var(--line-strong);
    background: #FAFAFC;
    font-size: 14px;
    color: var(--ink);
    transition: all 0.15s ease;
    font-family: inherit;
  }
  .text-input:focus {
    outline: none;
    border-color: var(--accent);
    background: #FFFFFF;
    box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.15);
  }
  .otp-input {
    height: 54px;
    font-family: "JetBrains Mono", monospace;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 10px;
    text-align: center;
    background: #F5F5F7;
  }
  .primary-btn {
    width: 100%;
    height: 46px;
    margin-top: 4px;
    border: none;
    border-radius: 999px;
    background: var(--accent);
    color: #FFFFFF;
    font-size: 14.5px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: background 0.15s ease, transform 0.1s ease;
    box-shadow: 0 4px 14px rgba(0, 113, 227, 0.28);
  }
  .primary-btn:hover:not(:disabled) {
    background: var(--accent-hover);
  }
  .primary-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .secondary-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 10px;
    font-size: 12.5px;
  }
  .link-btn {
    background: none;
    border: none;
    color: var(--accent);
    font-weight: 600;
    font-size: 12.5px;
    cursor: pointer;
    padding: 0;
  }
  .link-btn:disabled {
    color: var(--muted);
    cursor: not-allowed;
  }
  .status-banner {
    display: none;
    margin-bottom: 16px;
    padding: 11px 14px;
    border-radius: 11px;
    font-size: 13px;
    line-height: 1.45;
    font-weight: 500;
  }
  .status-banner.error {
    display: block;
    background: var(--danger-soft);
    border: 1px solid rgba(201, 52, 0, 0.25);
    color: var(--danger);
  }
  .status-banner.success {
    display: block;
    background: var(--success-soft);
    border: 1px solid rgba(29, 125, 63, 0.25);
    color: var(--success);
  }
  .or-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 24px 0 18px;
    color: var(--muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .or-divider::before,
  .or-divider::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--line);
  }
  .staff-box {
    background: #F5F5F7;
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 16px;
    text-align: center;
  }
  .staff-box-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--ink-secondary);
    margin-bottom: 10px;
  }
  .google-btn-slot {
    display: flex;
    justify-content: center;
    min-height: 42px;
  }
  .privacy-note {
    margin-top: 18px;
    font-size: 11.5px;
    line-height: 1.45;
    color: var(--muted);
    text-align: center;
  }
  .hidden { display: none !important; }

  @media (max-width: 980px) {
    .split-layout { grid-template-columns: 1fr; }
    .hero-pane { padding: 32px 24px; }
    .form-row-2 { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
  <div class="split-layout">
    <!-- Left Hero Pane -->
    <section class="hero-pane">
      <div class="brand-header">
        <div class="brand-logo-wrap">
          <div class="brand-mark">S</div>
          <div>
            <div class="brand-name">Sybyl Enterprise AI</div>
            <div class="brand-sub">Gemini Enterprise · Google ADK · Cloud Run</div>
          </div>
        </div>
      </div>

      <div class="hero-main">
        <div class="eyebrow-badge">
          <span class="eyebrow-dot"></span>
          <span>61 Deployed AI Agents · 8 Industry Sectors</span>
        </div>
        <h1 class="hero-title">Sign in once. Experience all 61 Enterprise AI Agents live.</h1>
        <p class="hero-subtitle">
          Built on Gemini Enterprise concepts with deterministic Python rules and Human-in-the-Loop approval. Verify your work email once to explore and launch every live agent for free.
        </p>

        <div class="workflow-box">
          <div class="workflow-label">How Single Sign-On &amp; Governance Work</div>
          <div class="workflow-steps">
            <div class="wf-step">
              <div class="wf-num">1</div>
              <div>
                <div class="wf-title">Passwordless Work Email or Sybyl Google Sign-In</div>
                <div class="wf-desc">Enter your work email for an instant 6-digit verification code — or use Google Sign-In if you are Sybyl staff.</div>
              </div>
            </div>
            <div class="wf-step">
              <div class="wf-num">2</div>
              <div>
                <div class="wf-title">Reasoning by Gemini · Rules &amp; Maths in Deterministic Python</div>
                <div class="wf-desc">The model reads documents and reasons; deterministic Python performs every calculation, rule check, and validation.</div>
              </div>
            </div>
            <div class="wf-step">
              <div class="wf-num">3</div>
              <div>
                <div class="wf-title">Zero Second Login · Human Approves Every Action</div>
                <div class="wf-desc">Your single sign-on session carries across all 61 agents, and a human approves before anything is posted, sent, or paid.</div>
              </div>
            </div>
          </div>
        </div>

        <div class="sector-pills-wrap">
          <span class="sector-pill">Banking &amp; Financial Services <strong>(12)</strong></span>
          <span class="sector-pill">Public Sector <strong>(11)</strong></span>
          <span class="sector-pill">Insurance <strong>(12)</strong></span>
          <span class="sector-pill">Sales &amp; Distribution <strong>(6)</strong></span>
          <span class="sector-pill">Finance Reconciliation <strong>(4)</strong></span>
          <span class="sector-pill">Retail Operations <strong>(3)</strong></span>
          <span class="sector-pill">Manufacturing &amp; Executive Data <strong>(4)</strong></span>
          <span class="sector-pill">Human Resources <strong>(9)</strong></span>
        </div>
      </div>

      <div class="hero-footer">
        <div class="trust-badges">
          <span class="trust-item">✓ Passwordless Work Email OTP</span>
          <span class="trust-item">✓ True Single Sign-On Handoff</span>
          <span class="trust-item">✓ Human-in-the-Loop Controls</span>
        </div>
        <div>© 2026 Sybyl Enterprise AI</div>
      </div>
    </section>

    <!-- Right Authentication & Lead Capture Pane -->
    <section class="auth-pane">
      <div class="auth-card">
        <div class="auth-badge">Free Enterprise Access · Single Sign-On</div>
        <h2 class="auth-title">Access the AI Agent Portfolio</h2>
        <p class="auth-subtitle">
          Sign in with your business email to unlock free interactive access to all 61 live agents across 8 sectors.
        </p>

        <div id="status-banner" class="status-banner" role="alert"></div>

        <!-- Step 1: Passwordless Work Email OTP Request Form -->
        <form id="otp-request-form" class="form-grid" novalidate>
          <div class="field-group">
            <label class="field-label" for="lead-email">
              <span>Work Email</span>
              <span class="field-hint">Business domains only</span>
            </label>
            <input id="lead-email" name="email" type="email" class="text-input" placeholder="name@company.com" required autocomplete="email" autofocus />
          </div>

          <button id="send-code-btn" type="submit" class="primary-btn">
            <span>Send 6-Digit Sign-In Code</span>
            <span>→</span>
          </button>
        </form>

        <!-- Step 2: 6-Digit OTP Verification Form -->
        <form id="otp-verify-form" class="form-grid hidden" novalidate>
          <div class="field-group">
            <label class="field-label" for="otp-code-input">
              <span>6-Digit Verification Code</span>
              <span id="otp-target-email" class="field-hint"></span>
            </label>
            <input id="otp-code-input" name="code" type="text" inputmode="numeric" maxlength="6" pattern="[0-9]{6}" class="text-input otp-input" placeholder="000000" required autocomplete="one-time-code" />
          </div>

          <button id="verify-code-btn" type="submit" class="primary-btn">
            <span>Verify &amp; Unlock All 61 Agents</span>
            <span>→</span>
          </button>

          <div class="secondary-actions">
            <button id="change-email-btn" type="button" class="link-btn">← Change email address</button>
            <button id="resend-code-btn" type="button" class="link-btn" disabled>Resend code (30s)</button>
          </div>
        </form>

        <!-- Secondary Option: Sybyl Staff Google Sign-In -->
        <div class="or-divider">OR — SYBYL STAFF SIGN-IN</div>

        <div class="staff-box">
          <div class="staff-box-label">Sybyl Team Members (<code>@sybyl.com</code>)</div>
          <div class="google-btn-slot">
            <div id="g_id_onload"
                 data-client_id="__OAUTH_CLIENT_ID__"
                 data-callback="handleGoogleCredentialResponse"
                 data-auto_prompt="false">
            </div>
            <div class="g_id_signin"
                 data-type="standard"
                 data-size="large"
                 data-theme="outline"
                 data-text="signin_with"
                 data-shape="pill"
                 data-logo_alignment="left"
                 data-width="340">
            </div>
          </div>
        </div>

        <div class="privacy-note">
          Personal email domains (Gmail, Yahoo, Outlook) are blocked on the passwordless form to ensure enterprise security.
        </div>
      </div>
    </section>
  </div>

<script>
  const NEXT_URL = __NEXT_URL_JSON__;
  let activeEmail = "";
  let resendTimer = null;

  const statusBanner = document.getElementById("status-banner");
  const requestForm = document.getElementById("otp-request-form");
  const verifyForm = document.getElementById("otp-verify-form");
  const sendCodeBtn = document.getElementById("send-code-btn");
  const verifyCodeBtn = document.getElementById("verify-code-btn");
  const changeEmailBtn = document.getElementById("change-email-btn");
  const resendCodeBtn = document.getElementById("resend-code-btn");
  const otpInput = document.getElementById("otp-code-input");
  const otpTargetEmail = document.getElementById("otp-target-email");

  function showStatus(msg, type = "error") {
    statusBanner.textContent = msg;
    statusBanner.className = "status-banner " + type;
  }

  function clearStatus() {
    statusBanner.textContent = "";
    statusBanner.className = "status-banner";
  }

  function startResendCooldown(seconds = 30) {
    let remaining = seconds;
    resendCodeBtn.disabled = true;
    resendCodeBtn.textContent = `Resend code (${remaining}s)`;
    if (resendTimer) clearInterval(resendTimer);
    resendTimer = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        clearInterval(resendTimer);
        resendCodeBtn.disabled = false;
        resendCodeBtn.textContent = "Resend code";
      } else {
        resendCodeBtn.textContent = `Resend code (${remaining}s)`;
      }
    }, 1000);
  }

  requestForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearStatus();

    const emailVal = document.getElementById("lead-email").value.trim();

    if (!emailVal) {
      showStatus("Please enter your work email address.", "error");
      return;
    }

    sendCodeBtn.disabled = true;
    sendCodeBtn.innerHTML = "<span>Sending verification code...</span>";

    try {
      const resp = await fetch("/auth/email/send-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: emailVal
        })
      });
      const data = await resp.json();
      if (!resp.ok) {
        showStatus(data.error || "Could not send verification code.", "error");
        return;
      }

      activeEmail = emailVal;
      otpTargetEmail.textContent = emailVal;

      requestForm.classList.add("hidden");
      verifyForm.classList.remove("hidden");
      showStatus(data.message || `We sent a 6-digit code to ${emailVal}.`, "success");
      startResendCooldown(30);
      otpInput.value = "";
      otpInput.focus();
    } catch (err) {
      showStatus("Network error while requesting verification code. Please try again.", "error");
    } finally {
      sendCodeBtn.disabled = false;
      sendCodeBtn.innerHTML = "<span>Send 6-Digit Sign-In Code</span><span>→</span>";
    }
  });

  verifyForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearStatus();
    const codeVal = otpInput.value.trim();
    if (codeVal.length !== 6) {
      showStatus("Please enter the 6-digit numeric verification code.", "error");
      return;
    }

    verifyCodeBtn.disabled = true;
    verifyCodeBtn.innerHTML = "<span>Verifying code...</span>";

    try {
      const resp = await fetch("/auth/email/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: activeEmail,
          code: codeVal
        })
      });
      const data = await resp.json();
      if (!resp.ok) {
        showStatus(data.error || "Invalid verification code.", "error");
        return;
      }
      if (data.user) {
        seedClientSsoStorage(data.user);
      }
      window.location.href = data.redirect || NEXT_URL || "/";
    } catch (err) {
      showStatus("Network error while verifying code. Please try again.", "error");
    } finally {
      verifyCodeBtn.disabled = false;
      verifyCodeBtn.innerHTML = "<span>Verify &amp; Unlock All 61 Agents</span><span>→</span>";
    }
  });

  changeEmailBtn.addEventListener("click", () => {
    clearStatus();
    verifyForm.classList.add("hidden");
    requestForm.classList.remove("hidden");
  });

  resendCodeBtn.addEventListener("click", async () => {
    if (!activeEmail) return;
    clearStatus();
    resendCodeBtn.disabled = true;
    try {
      const resp = await fetch("/auth/email/send-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: activeEmail
        })
      });
      const data = await resp.json();
      if (!resp.ok) {
        showStatus(data.error || "Could not resend code.", "error");
        resendCodeBtn.disabled = false;
        return;
      }
      showStatus(`A new 6-digit verification code was sent to ${activeEmail}.`, "success");
      startResendCooldown(30);
    } catch (err) {
      showStatus("Failed to resend verification code.", "error");
      resendCodeBtn.disabled = false;
    }
  });

  window.handleGoogleCredentialResponse = async function(response) {
    clearStatus();
    if (!response || !response.credential) {
      showStatus("Google Sign-In did not return a credential.", "error");
      return;
    }
    try {
      const resp = await fetch("/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: response.credential })
      });
      const data = await resp.json();
      if (!resp.ok) {
        showStatus(data.error || "Google Sign-In failed.", "error");
        return;
      }
      if (data.user) {
        seedClientSsoStorage(data.user, response.credential);
      }
      window.location.href = data.redirect || NEXT_URL || "/";
    } catch (err) {
      showStatus("Network error verifying Google Sign-In.", "error");
    }
  };

  function seedClientSsoStorage(user, rawIdToken = "") {
    try {
      const profile = {
        email: user.email,
        name: user.name || user.email,
        company: user.company || "Enterprise",
        role: user.role || "Executive",
        picture: user.picture || "",
        provider: user.provider || "email_otp",
        authenticated: true
      };
      const jsonStr = JSON.stringify(profile);
      const keys = __SSO_STORAGE_KEYS_JSON__;
      for (const k of keys) {
        localStorage.setItem(k, jsonStr);
        sessionStorage.setItem(k, jsonStr);
      }
      localStorage.setItem("sybyl_sso_user", jsonStr);
      localStorage.setItem("sybyl_portal_authenticated", "true");
      localStorage.setItem("supplier_prequal_portal_authenticated", "true");
      sessionStorage.setItem("hr_google_id_token", rawIdToken || ("demo-token:" + user.email));
    } catch (_) {}
  }
</script>
</body>
</html>
"""
