"""Sybyl Agentic AI Portfolio & Lead-Generation Single Sign-On Portal.

Provides:
- /login : Split-screen Passwordless Work Email OTP (Lead Capture) + Sybyl Staff Google Sign-In
- /      : Authenticated Portfolio Directory of all 61 deployed agents across 8 sectors
- /launch/{slug} & /app/{slug}/... : True Single Sign-On Handoff & Reverse-Proxy Gateway
- /admin & /api/admin/leads.csv    : Marketing Leads & Usage Telemetry Dashboard + CSV Export
"""

from __future__ import annotations

import html
import json
import logging
import os
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware

from auth import (
    LOGIN_PAGE_TEMPLATE,
    SESSION_MAX_AGE_SECONDS,
    check_work_email_allowed,
    get_admin_emails,
    get_allowed_domains,
    get_allowed_emails,
    get_oauth_client_id,
    get_session_secret,
    is_admin_user,
    is_open_business_signup,
    verify_google_credential,
)
from catalog import AGENTS_BY_SLUG, AGENTS_CATALOG, DESIGN_PRINCIPLES, SECTORS_ORDER, get_catalog_summary
from leads import (
    export_leads_csv,
    get_admin_telemetry,
    infer_company_from_domain,
    infer_name_from_email,
    record_agent_launch,
    record_lead_login,
)
from mail import send_otp_email
from otp import OTPRateLimitError, issue_otp, verify_otp
from sso_gateway import SSO_STORAGE_KEYS, proxy_agent_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sybyl Enterprise AI Portfolio — Single Sign-On & Lead Portal",
    version="1.0.0",
)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


def _current_user(request: Request) -> dict[str, Any] | None:
    session = request.scope.get("session") or {}
    user = session.get("user")
    if not isinstance(user, dict) or not user.get("email"):
        return None
    exp = user.get("exp")
    if exp and int(time.time()) > int(exp):
        session.pop("user", None)
        return None
    return user


# =============================================================================
# Health & Metadata Endpoints
# =============================================================================


@app.get("/_health")
@app.get("/api/health")
async def health_check() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": "sybyl-agent-portfolio",
            "total_agents": len(AGENTS_CATALOG),
            "total_sectors": len(SECTORS_ORDER),
            "open_business_signup": is_open_business_signup(),
        }
    )


@app.get("/api/catalog")
async def api_catalog(request: Request) -> JSONResponse:
    user = _current_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required."}, status_code=401)
    return JSONResponse(get_catalog_summary())


@app.get("/auth/me")
async def auth_me(request: Request) -> JSONResponse:
    user = _current_user(request)
    if not user:
        return JSONResponse({"authenticated": False}, status_code=401)
    return JSONResponse(
        {
            "authenticated": True,
            "user": {
                **user,
                "is_admin": is_admin_user(user.get("email", "")),
            },
        }
    )


# =============================================================================
# Authentication & Lead Capture Routes (/login, /auth/*)
# =============================================================================


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    user = _current_user(request)
    next_url = request.query_params.get("next") or "/"
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"
    if user:
        return RedirectResponse(next_url, status_code=302)

    rendered = (
        LOGIN_PAGE_TEMPLATE.replace("__OAUTH_CLIENT_ID__", html.escape(get_oauth_client_id()))
        .replace("__NEXT_URL_JSON__", json.dumps(next_url))
        .replace("__SSO_STORAGE_KEYS_JSON__", json.dumps(SSO_STORAGE_KEYS))
    )
    return HTMLResponse(
        rendered,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.post("/auth/email/send-otp")
async def auth_send_otp(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON request body."}, status_code=400)

    email = str(body.get("email") or "").strip().lower()
    name = str(body.get("name") or "").strip()
    company = str(body.get("company") or "").strip()
    role = str(body.get("role") or "").strip()
    terms_accepted = bool(body.get("terms_accepted", False))

    allowed, reason = check_work_email_allowed(email)
    if not allowed:
        return JSONResponse({"error": reason}, status_code=403)

    is_sybyl_staff = email.endswith("@sybyl.com")
    if not is_sybyl_staff and not terms_accepted:
        return JSONResponse(
            {
                "error": (
                    "External visitors must accept the Terms & Conditions and "
                    "Use-at-Your-Own-Risk Data Processing Disclaimer before signing in."
                )
            },
            status_code=400,
        )

    client_ip = _client_ip(request)
    try:
        code, ttl_seconds = issue_otp(
            email=email,
            client_ip=client_ip,
            name=name,
            company=company,
            role=role,
        )
    except OTPRateLimitError as rl_exc:
        return JSONResponse(
            {
                "error": str(rl_exc),
                "retry_after_seconds": rl_exc.retry_after_seconds,
            },
            status_code=429,
        )

    try:
        send_otp_email(
            to_email=email,
            code=code,
            ttl_seconds=ttl_seconds,
            recipient_name=name,
        )
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", email, exc)
        return JSONResponse(
            {
                "error": (
                    "Could not dispatch verification email right now. "
                    "Please check your email address or try again in a moment."
                )
            },
            status_code=502,
        )

    return JSONResponse(
        {
            "ok": True,
            "email": email,
            "expires_in_seconds": ttl_seconds,
            "message": f"We sent a 6-digit verification code to {email}.",
        }
    )


@app.post("/auth/email/verify-otp")
async def auth_verify_otp(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON request body."}, status_code=400)

    email = str(body.get("email") or "").strip().lower()
    code = str(body.get("code") or "").strip()
    req_name = str(body.get("name") or "").strip()
    req_company = str(body.get("company") or "").strip()
    req_role = str(body.get("role") or "").strip()

    allowed, reason = check_work_email_allowed(email)
    if not allowed:
        return JSONResponse({"error": reason}, status_code=403)

    ok, verify_reason, meta = verify_otp(email=email, code=code)
    if not ok:
        return JSONResponse({"error": verify_reason}, status_code=401)

    domain = email.split("@", 1)[1].strip().lower() if "@" in email else ""
    final_name = req_name or meta.get("name") or infer_name_from_email(email)
    final_company = req_company or meta.get("company") or infer_company_from_domain(domain)
    final_role = req_role or meta.get("role") or "Business Leader"

    lead_record = record_lead_login(
        email=email,
        name=final_name,
        company=final_company,
        role=final_role,
        provider="email_otp",
        client_ip=_client_ip(request),
        terms_accepted=True,
        terms_version="2026.1",
    )

    now = int(time.time())
    session_user = {
        "email": email,
        "name": lead_record.get("name") or final_name,
        "company": lead_record.get("company") or final_company,
        "role": lead_record.get("role") or final_role,
        "domain": domain,
        "picture": "",
        "provider": "email_otp",
        "is_admin": is_admin_user(email),
        "iat": now,
        "exp": now + SESSION_MAX_AGE_SECONDS,
    }
    request.session["user"] = session_user

    return JSONResponse(
        {
            "ok": True,
            "user": session_user,
            "redirect": "/",
        }
    )


@app.post("/auth/google")
async def auth_google(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON request body."}, status_code=400)

    credential = str(body.get("credential") or "").strip()
    if not credential:
        return JSONResponse({"error": "Missing Google credential token."}, status_code=400)

    try:
        verified = verify_google_credential(credential)
    except PermissionError as p_exc:
        return JSONResponse({"error": str(p_exc)}, status_code=403)
    except ValueError as v_exc:
        return JSONResponse({"error": str(v_exc)}, status_code=401)

    email = verified["email"]
    lead_record = record_lead_login(
        email=email,
        name=verified.get("name", ""),
        company=verified.get("company", "Sybyl"),
        role=verified.get("role", "Sybyl Staff"),
        provider="google",
        picture=verified.get("picture", ""),
        client_ip=_client_ip(request),
    )

    session_user = {
        **verified,
        "company": lead_record.get("company") or verified.get("company", "Sybyl"),
        "role": lead_record.get("role") or verified.get("role", "Sybyl Staff"),
        "is_admin": is_admin_user(email),
    }
    request.session["user"] = session_user

    return JSONResponse(
        {
            "ok": True,
            "user": session_user,
            "redirect": "/",
        }
    )


@app.get("/auth/logout")
@app.post("/auth/logout")
async def auth_logout(request: Request) -> Response:
    request.session.clear()
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("sybyl_active_agent", path="/")
    return resp


@app.get("/Sybyl-Logo.svg")
@app.get("/static/Sybyl-Logo.svg")
async def serve_sybyl_logo() -> Response:
    """Serve the official Sybyl vector logo across all portal pages."""
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Sybyl-Logo.svg")
    with open(logo_path, "r", encoding="utf-8") as f:
        svg_content = f.read()
    return Response(
        content=svg_content,
        media_type="image/svg+xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/terms", response_class=HTMLResponse)
async def terms_and_conditions_page() -> HTMLResponse:
    """Standalone Legal Terms & Conditions, Data Processing & Risk Disclaimer page."""
    html_doc = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Terms &amp; Conditions, Data Processing &amp; Risk Disclaimer — Sybyl Enterprise AI</title>
<style>
  :root {
    --bg: #F5F5F7;
    --surface: #FFFFFF;
    --ink: #1D1D1F;
    --ink-secondary: #515154;
    --muted: #86868B;
    --line: #E5E5EA;
    --accent: #0071E3;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
    line-height: 1.6;
    padding: 40px 20px;
  }
  .card {
    max-width: 820px;
    margin: 0 auto;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 36px 40px;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.05);
  }
  .eyebrow {
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
    margin-bottom: 6px;
  }
  h1 {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-bottom: 12px;
  }
  .lead {
    font-size: 14px;
    color: var(--ink-secondary);
    padding-bottom: 20px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 22px;
  }
  h2 {
    font-size: 15.5px;
    font-weight: 700;
    color: var(--ink);
    margin: 18px 0 6px;
  }
  p {
    font-size: 14px;
    color: var(--ink-secondary);
    margin-bottom: 12px;
  }
  .footer-bar {
    margin-top: 28px;
    padding-top: 18px;
    border-top: 1px solid var(--line);
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12.5px;
    color: var(--muted);
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 9px 16px;
    border-radius: 999px;
    background: var(--accent);
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
    text-decoration: none;
  }
</style>
</head>
<body>
  <main class="card">
    <div style="margin-bottom: 16px;">
      <img src="/Sybyl-Logo.svg" alt="Sybyl" style="height: 36px; width: auto; display: block;" />
    </div>
    <div class="eyebrow">Sybyl Enterprise AI Portfolio · Legal Notice (Version 2026.1)</div>
    <h1>Terms &amp; Conditions, Data Processing &amp; Risk Disclaimer</h1>
    <p class="lead">
      <strong>Mandatory for External (Non-Sybyl) Visitors:</strong> By verifying your business email address and accessing the Sybyl Agentic AI Portfolio, you agree to the following Terms &amp; Conditions on behalf of yourself and your organisation.
    </p>

    <h2>1. No Account Creation &amp; Business Email-Only Capture</h2>
    <p>
      You do not need to create an account with Sybyl to access this portfolio, and signing in does not create a customer account, user profile, or service agreement with Sybyl. The only information Sybyl captures and records is your <strong>business email address</strong> (for one-time passcode verification and business communications). Sybyl does not maintain any other records of your account.
    </p>

    <h2>2. User-Initiated Uploads &amp; Zero Data Storage by Sybyl</h2>
    <p>
      Any documents, files, statements, contracts, invoices, images, audio recordings, or text prompts that you upload or enter into any of the 61 applications are uploaded strictly on your own initiative and responsibility. <strong>Sybyl does not capture, store, archive, or maintain permanent records of any documents or business data you upload into these applications.</strong>
    </p>

    <h2>3. Corporate Google Gemini Enterprise Safeguards &amp; Zero Model Training</h2>
    <p>
      The applications in this portfolio process uploaded documents and inputs through Sybyl's corporate <strong>Google Gemini Enterprise</strong> engine governed by Google Cloud's enterprise data privacy commitments. <strong>Your uploaded documents, prompts, and generated outputs are protected by enterprise-grade safeguards and are never used to train Google's foundation models or shared with third parties.</strong> Sybyl itself does not store, inspect, or retain copies of your uploaded data.
    </p>

    <h2>4. Generative AI Safeguard ("AI Can Make Mistakes") &amp; Human Verification</h2>
    <p>
      <strong>Generative AI can make mistakes, misinterpret documents, or produce incomplete outputs.</strong> While deterministic Python performs calculations and rule validations within these agents, all outputs are provided strictly as decision-support drafts. Users must independently review and verify all figures, citations, and recommendations with a qualified human professional before any action, filing, communication, or payment is taken.
    </p>

    <h2>5. Assumption of Risk ("Use at Your Own Risk") &amp; "AS IS" Provision</h2>
    <p>
      <strong>Users access and use these applications, and upload any files or data, strictly at their own sole risk.</strong> All 61 applications and their outputs are provided on an <strong>"AS IS"</strong> and <strong>"AS AVAILABLE"</strong> basis for demonstration and evaluation purposes only, without warranties of any kind (express or implied), including accuracy, completeness, merchantability, fitness for a particular purpose, or regulatory compliance.
    </p>

    <h2>6. Limitation of Liability &amp; Indemnification</h2>
    <p>
      To the fullest extent permitted by applicable law, Sybyl, its affiliates, directors, officers, and employees disclaim all liability for any direct, indirect, incidental, consequential, or special damages, loss of data, regulatory claims, or business decisions arising from your use of the applications or any data you upload. You agree to indemnify and hold Sybyl harmless from any claims arising out of data or documents you submit to the applications.
    </p>

    <div class="footer-bar">
      <span>© 2026 Sybyl Enterprise AI · All rights reserved.</span>
      <a href="/login" class="btn">← Back to Sign-In</a>
    </div>
  </main>
</body>
</html>"""
    return HTMLResponse(html_doc)


# =============================================================================
# Page 2: Authenticated Agentic AI Portfolio Directory (/)
# =============================================================================


def _render_portfolio_page(user: dict[str, Any]) -> str:
    summary = get_catalog_summary()
    user_name = html.escape(str(user.get("name") or user.get("email") or "Guest"))
    user_email = html.escape(str(user.get("email") or ""))
    user_company = html.escape(str(user.get("company") or "Enterprise"))
    user_role = html.escape(str(user.get("role") or ""))
    is_admin = is_admin_user(user.get("email", ""))

    admin_btn_html = ""
    if is_admin:
        admin_btn_html = """
        <a href="/admin" class="nav-pill-btn nav-admin-btn" title="Marketing Leads &amp; Usage Telemetry">
          <span>📊 Marketing Leads &amp; Telemetry</span>
        </a>
        """

    # Build sector filter pills
    filter_pills_html = [
        f'<button type="button" class="sector-tab active" data-sector="ALL">'
        f'<span>All Sectors</span><span class="tab-count">{summary["total_agents"]}</span></button>'
    ]
    for sec in summary["sectors"]:
        filter_pills_html.append(
            f'<button type="button" class="sector-tab" data-sector="{html.escape(sec["slug"])}">'
            f'<span>{html.escape(sec["name"])}</span>'
            f'<span class="tab-count">{sec["count"]}</span></button>'
        )

    # Build sector sections and agent cards
    sector_sections_html: list[str] = []
    for sec in summary["sectors"]:
        cards_html: list[str] = []
        for agent in sec["agents"]:
            slug = html.escape(agent["slug"])
            title = html.escape(agent["title"])
            what_it_does = html.escape(agent["what_it_does"])
            value_text = html.escape(agent["value"])
            live_url = html.escape(agent["live_url"])
            sec_name = html.escape(agent["sector"])
            accent = html.escape(agent["sector_accent"])

            channel_badge_html = ""
            if agent.get("channel_badge"):
                channel_badge_html = (
                    f'<span class="channel-badge">{html.escape(agent["channel_badge"])}</span>'
                )

            secondary_btn_html = ""
            if agent.get("secondary_url"):
                sec_url = html.escape(agent["secondary_url"])
                sec_lbl = html.escape(agent.get("secondary_label") or "Secondary View")
                secondary_btn_html = (
                    f'<a href="{sec_url}" target="_blank" rel="noopener" class="btn-secondary-link">'
                    f'{sec_lbl} ↗</a>'
                )

            search_blob = html.escape(
                f"{agent['title']} {agent['sector']} {agent['what_it_does']} {agent['value']}".lower()
            )

            cards_html.append(
                f"""
                <article class="agent-card" data-sector="{html.escape(sec['slug'])}" data-search="{search_blob}">
                  <div class="card-top">
                    <div class="card-badges">
                      <span class="agent-num-pill" style="color:{accent};background:{accent}14;border-color:{accent}30;">#{agent['id']}</span>
                      <span class="agent-sector-pill">{sec_name}</span>
                      {channel_badge_html}
                    </div>
                    <span class="sso-ready-pill" title="Pre-authenticated via Single Sign-On">
                      <span class="sso-dot"></span>SSO Ready
                    </span>
                  </div>

                  <h3 class="agent-title">{title}</h3>

                  <div class="agent-body">
                    <div class="agent-block">
                      <div class="block-label">What it does</div>
                      <p class="block-text">{what_it_does}</p>
                    </div>

                    <div class="agent-value-box">
                      <div class="value-label">Business Value</div>
                      <p class="value-text">{value_text}</p>
                    </div>
                  </div>

                  <div class="card-actions">
                    <a href="/launch/{slug}" class="btn-launch-sso">
                      <span>Launch Agent (SSO)</span>
                      <span aria-hidden="true">→</span>
                    </a>
                    {secondary_btn_html}
                    <a href="{live_url}" target="_blank" rel="noopener" class="btn-direct-url" title="Open direct Cloud Run URL in new tab">
                      <span>Direct ↗</span>
                    </a>
                  </div>
                </article>
                """
            )

        sector_sections_html.append(
            f"""
            <section class="sector-section" id="sector-{html.escape(sec['slug'])}" data-sector-section="{html.escape(sec['slug'])}">
              <div class="sector-header">
                <div>
                  <div class="sector-eyebrow" style="color:{html.escape(sec['accent'])};">
                    SECTOR · {sec['count']} LIVE AGENTS
                  </div>
                  <h2 class="sector-title">{html.escape(sec['name'])}</h2>
                  <p class="sector-tagline">{html.escape(sec['tagline'])}</p>
                </div>
                <div class="sector-count-badge">{sec['count']} Agents</div>
              </div>
              <div class="agents-grid">
                {''.join(cards_html)}
              </div>
            </section>
            """
        )

    user_json = json.dumps(
        {
            "email": user.get("email", ""),
            "name": user.get("name", ""),
            "company": user.get("company", ""),
            "role": user.get("role", ""),
            "picture": user.get("picture", ""),
            "provider": user.get("provider", "email_otp"),
            "authenticated": True,
        }
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Sybyl Agentic AI Portfolio — 61 Live Enterprise Agents Across 8 Sectors</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script>
  // Ensure browser localStorage & sessionStorage are pre-seeded with the active SSO session
  (function() {{
    try {{
      var profile = {user_json};
      var profileStr = JSON.stringify(profile);
      var keys = {json.dumps(SSO_STORAGE_KEYS)};
      for (var i = 0; i < keys.length; i++) {{
        localStorage.setItem(keys[i], profileStr);
        sessionStorage.setItem(keys[i], profileStr);
      }}
      localStorage.setItem("sybyl_sso_user", profileStr);
      localStorage.setItem("sybyl_portal_authenticated", "true");
      localStorage.setItem("supplier_prequal_portal_authenticated", "true");
      if (!sessionStorage.getItem("hr_google_id_token")) {{
        sessionStorage.setItem("hr_google_id_token", "demo-token:" + profile.email);
      }}
    }} catch (_) {{}}
  }})();
</script>
<style>
  :root {{
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
    --success-soft: #EBF7EE;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif;
    background: var(--bg);
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
    padding-bottom: 80px;
  }}
  /* Top Frosted Navigation Bar */
  .topbar {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(255, 255, 255, 0.86);
    backdrop-filter: saturate(180%) blur(20px);
    border-bottom: 1px solid var(--line);
    padding: 14px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }}
  .brand-cluster {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .brand-logo-svg {{
    height: 36px;
    width: auto;
    display: block;
  }}
  .brand-title {{
    font-size: 16.5px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--ink);
  }}
  .brand-subtitle {{
    font-size: 12px;
    color: var(--muted);
    font-weight: 500;
  }}
  .user-cluster {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }}
  .user-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    border-radius: 999px;
    background: #F5F5F7;
    border: 1px solid var(--line);
    font-size: 12.5px;
    font-weight: 600;
    color: var(--ink);
  }}
  .user-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #30D158;
  }}
  .user-meta {{
    color: var(--muted);
    font-weight: 500;
  }}
  .nav-pill-btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border-radius: 999px;
    font-size: 12.5px;
    font-weight: 600;
    text-decoration: none;
    border: 1px solid var(--line-strong);
    color: var(--ink);
    background: #FFFFFF;
    transition: all 0.15s ease;
  }}
  .nav-pill-btn:hover {{
    border-color: var(--accent);
    color: var(--accent);
  }}
  .nav-admin-btn {{
    background: var(--accent-soft);
    border-color: rgba(0, 113, 227, 0.25);
    color: var(--accent);
  }}

  /* Hero & Design Principles Section */
  .container {{
    max-width: 1380px;
    margin: 0 auto;
    padding: 0 28px;
  }}
  .hero-banner {{
    margin-top: 28px;
    background: linear-gradient(145deg, #0B101E 0%, #152244 100%);
    border-radius: 24px;
    padding: 38px 42px;
    color: #FFFFFF;
    box-shadow: 0 18px 45px rgba(11, 16, 30, 0.12);
  }}
  .hero-top {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    flex-wrap: wrap;
    margin-bottom: 28px;
  }}
  .hero-eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 5px 13px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.18);
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #7CC0FF;
    margin-bottom: 14px;
  }}
  .hero-h1 {{
    font-size: clamp(26px, 2.8vw, 36px);
    font-weight: 800;
    letter-spacing: -0.03em;
    margin-bottom: 10px;
  }}
  .hero-lead {{
    font-size: 15px;
    line-height: 1.58;
    color: rgba(255, 255, 255, 0.8);
    max-width: 820px;
  }}
  .hero-stats {{
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
  }}
  .stat-card {{
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 16px;
    padding: 14px 20px;
    min-width: 120px;
    text-align: center;
  }}
  .stat-num {{
    font-size: 26px;
    font-weight: 800;
    color: #7CC0FF;
    line-height: 1.1;
  }}
  .stat-lbl {{
    font-size: 11.5px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
    margin-top: 4px;
  }}
  .principles-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    padding-top: 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.12);
  }}
  .principle-card {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 16px 18px;
  }}
  .principle-title {{
    font-size: 13.5px;
    font-weight: 700;
    color: #7CC0FF;
    margin-bottom: 5px;
  }}
  .principle-desc {{
    font-size: 13px;
    line-height: 1.48;
    color: rgba(255, 255, 255, 0.82);
  }}

  /* Search & Sector Filter Controls */
  .controls-bar {{
    margin-top: 24px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 18px 22px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.03);
  }}
  .search-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }}
  .search-input-wrap {{
    flex: 1;
    min-width: 280px;
    position: relative;
  }}
  .search-input {{
    width: 100%;
    height: 44px;
    padding: 0 16px 0 42px;
    border-radius: 12px;
    border: 1px solid var(--line-strong);
    background: #F5F5F7;
    font-size: 14.5px;
    color: var(--ink);
    font-family: inherit;
    transition: all 0.15s ease;
  }}
  .search-input:focus {{
    outline: none;
    background: #FFFFFF;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.15);
  }}
  .search-icon {{
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--muted);
    font-size: 15px;
    pointer-events: none;
  }}
  .results-counter {{
    font-size: 13px;
    font-weight: 600;
    color: var(--ink-secondary);
  }}
  .sector-tabs {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}
  .sector-tab {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 8px 14px;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: #F5F5F7;
    color: var(--ink-secondary);
    font-size: 12.8px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s ease;
  }}
  .sector-tab:hover {{
    border-color: var(--accent);
    color: var(--ink);
  }}
  .sector-tab.active {{
    background: var(--accent);
    border-color: var(--accent);
    color: #FFFFFF;
  }}
  .tab-count {{
    padding: 1px 7px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    background: rgba(0, 0, 0, 0.07);
  }}
  .sector-tab.active .tab-count {{
    background: rgba(255, 255, 255, 0.24);
    color: #FFFFFF;
  }}

  /* Sector Sections & Agent Cards Grid */
  .sector-section {{
    margin-top: 38px;
  }}
  .sector-header {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--line);
    flex-wrap: wrap;
  }}
  .sector-eyebrow {{
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 4px;
  }}
  .sector-title {{
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.025em;
    color: var(--ink);
    margin-bottom: 4px;
  }}
  .sector-tagline {{
    font-size: 13.8px;
    color: var(--ink-secondary);
  }}
  .sector-count-badge {{
    padding: 6px 14px;
    border-radius: 999px;
    background: var(--surface);
    border: 1px solid var(--line);
    font-size: 12.5px;
    font-weight: 700;
    color: var(--ink-secondary);
  }}
  .agents-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(390px, 1fr));
    gap: 20px;
  }}
  .agent-card {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.025);
  }}
  .agent-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 14px 32px rgba(0, 0, 0, 0.07);
    border-color: rgba(0, 113, 227, 0.35);
  }}
  .card-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }}
  .card-badges {{
    display: flex;
    align-items: center;
    gap: 7px;
    flex-wrap: wrap;
  }}
  .agent-num-pill {{
    font-size: 11.5px;
    font-weight: 800;
    padding: 3px 9px;
    border-radius: 999px;
    border: 1px solid transparent;
  }}
  .agent-sector-pill {{
    font-size: 11.5px;
    font-weight: 600;
    color: var(--ink-secondary);
    background: #F5F5F7;
    padding: 3px 10px;
    border-radius: 999px;
  }}
  .channel-badge {{
    font-size: 11px;
    font-weight: 700;
    color: #1D7D3F;
    background: #EBF7EE;
    padding: 3px 9px;
    border-radius: 999px;
  }}
  .sso-ready-pill {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    font-weight: 600;
    color: var(--success);
  }}
  .sso-dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #30D158;
  }}
  .agent-title {{
    font-size: 18px;
    font-weight: 800;
    line-height: 1.3;
    letter-spacing: -0.015em;
    color: var(--ink);
    margin-bottom: 14px;
  }}
  .agent-body {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
    flex: 1;
  }}
  .block-label {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    margin-bottom: 4px;
  }}
  .block-text {{
    font-size: 13.6px;
    line-height: 1.52;
    color: var(--ink-secondary);
  }}
  .agent-value-box {{
    background: #F5F9FF;
    border: 1px solid rgba(0, 113, 227, 0.16);
    border-radius: 12px;
    padding: 11px 13px;
  }}
  .value-label {{
    font-size: 10.5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent);
    margin-bottom: 3px;
  }}
  .value-text {{
    font-size: 13px;
    line-height: 1.45;
    font-weight: 500;
    color: var(--ink);
  }}
  .card-actions {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding-top: 14px;
    border-top: 1px solid var(--line);
    flex-wrap: wrap;
  }}
  .btn-launch-sso {{
    flex: 1;
    min-width: 170px;
    height: 40px;
    border-radius: 999px;
    background: var(--accent);
    color: #FFFFFF;
    font-size: 13.5px;
    font-weight: 600;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    transition: background 0.15s ease;
    box-shadow: 0 4px 12px rgba(0, 113, 227, 0.22);
  }}
  .btn-launch-sso:hover {{
    background: var(--accent-hover);
  }}
  .btn-secondary-link,
  .btn-direct-url {{
    height: 40px;
    padding: 0 13px;
    border-radius: 999px;
    border: 1px solid var(--line-strong);
    background: #FFFFFF;
    color: var(--ink-secondary);
    font-size: 12.5px;
    font-weight: 600;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }}
  .btn-secondary-link:hover,
  .btn-direct-url:hover {{
    border-color: var(--accent);
    color: var(--accent);
  }}
  .empty-state {{
    display: none;
    margin-top: 32px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 48px 24px;
    text-align: center;
    color: var(--ink-secondary);
  }}
  .hidden {{ display: none !important; }}

  @media (max-width: 900px) {{
    .principles-grid {{ grid-template-columns: 1fr; }}
    .agents-grid {{ grid-template-columns: 1fr; }}
    .topbar {{ padding: 12px 18px; }}
    .hero-banner {{ padding: 28px 22px; }}
  }}
</style>
</head>
<body>
  <header class="topbar">
    <div class="brand-cluster">
      <img src="/Sybyl-Logo.svg" alt="Sybyl" class="brand-logo-svg" />
      <div>
        <div class="brand-title">Sybyl Agentic AI Portfolio</div>
        <div class="brand-subtitle">61 Live Agents Across 8 Industry Sectors · Single Sign-On Active</div>
      </div>
    </div>

    <div class="user-cluster">
      <div class="user-badge" title="Signed in via Single Sign-On">
        <span class="user-dot"></span>
        <span>{user_name}</span>
        <span class="user-meta">· {user_company} ({user_email})</span>
      </div>
      {admin_btn_html}
      <a href="/auth/logout" class="nav-pill-btn">Sign Out</a>
    </div>
  </header>

  <main class="container">
    <section class="hero-banner">
      <div class="hero-top">
        <div>
          <div class="hero-eyebrow">Gemini Enterprise · Google Agent Development Kit · Cloud Run</div>
          <h1 class="hero-h1">Enterprise Agentic AI Portfolio</h1>
          <p class="hero-lead">
            Complete list of deployed agents (61 listings across 8 sectors). Built on Gemini Enterprise concepts (Gemini models, Google Agent Development Kit, Cloud Run on Google Cloud). The design is flexible and ports to other models and agent frameworks, including locally hosted models.
          </p>
        </div>
        <div class="hero-stats">
          <div class="stat-card">
            <div class="stat-num">61</div>
            <div class="stat-lbl">Live AI Agents</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">8</div>
            <div class="stat-lbl">Industry Sectors</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">1-Click</div>
            <div class="stat-lbl">SSO Launch</div>
          </div>
        </div>
      </div>

      <div class="principles-grid">
        <div class="principle-card">
          <div class="principle-title">1. Reasoning + Deterministic Python</div>
          <div class="principle-desc">The model does reasoning and document reading; deterministic Python does calculations, rules and validation.</div>
        </div>
        <div class="principle-card">
          <div class="principle-title">2. Human-in-the-Loop Approval</div>
          <div class="principle-desc">A human approves before anything is posted, sent or paid.</div>
        </div>
        <div class="principle-card">
          <div class="principle-title">3. Enterprise Single Sign-On</div>
          <div class="principle-desc">Enterprise sign-in on every agent — your active session launches any agent below with zero second login.</div>
        </div>
      </div>
    </section>

    <section class="controls-bar" aria-label="Filter and search agents">
      <div class="search-row">
        <div class="search-input-wrap">
          <span class="search-icon">🔍</span>
          <input id="agent-search-input" type="search" class="search-input" placeholder="Search 61 agents by name, sector, document type, or business value..." />
        </div>
        <div id="visible-count-label" class="results-counter">Showing all 61 agents across 8 sectors</div>
      </div>
      <div class="sector-tabs" id="sector-tabs">
        {''.join(filter_pills_html)}
      </div>
    </section>

    <div id="empty-search-state" class="empty-state">
      <h3 style="font-size:18px;margin-bottom:6px;color:#1D1D1F;">No matching agents found</h3>
      <p style="font-size:14px;">Try clearing your search filter or selecting "All Sectors".</p>
    </div>

    {''.join(sector_sections_html)}
  </main>

  <script>
    (function() {{
      const searchInput = document.getElementById("agent-search-input");
      const sectorTabs = document.querySelectorAll(".sector-tab");
      const cards = document.querySelectorAll(".agent-card");
      const sections = document.querySelectorAll(".sector-section");
      const countLabel = document.getElementById("visible-count-label");
      const emptyState = document.getElementById("empty-search-state");

      let activeSector = "ALL";

      function applyFilters() {{
        const q = (searchInput.value || "").trim().toLowerCase();
        let visibleCards = 0;
        let visibleSectors = 0;

        sections.forEach((sec) => {{
          const secSlug = sec.getAttribute("data-sector-section");
          const secCards = sec.querySelectorAll(".agent-card");
          let secVisible = 0;

          secCards.forEach((card) => {{
            const matchesSector = (activeSector === "ALL" || secSlug === activeSector);
            const searchBlob = card.getAttribute("data-search") || "";
            const matchesQuery = (!q || searchBlob.includes(q));
            if (matchesSector && matchesQuery) {{
              card.classList.remove("hidden");
              secVisible += 1;
              visibleCards += 1;
            }} else {{
              card.classList.add("hidden");
            }}
          }});

          if (secVisible > 0) {{
            sec.classList.remove("hidden");
            visibleSectors += 1;
          }} else {{
            sec.classList.add("hidden");
          }}
        }});

        countLabel.textContent = `Showing ${{visibleCards}} agent${{visibleCards === 1 ? "" : "s"}} across ${{visibleSectors}} sector${{visibleSectors === 1 ? "" : "s"}}`;
        emptyState.style.display = visibleCards === 0 ? "block" : "none";
      }}

      sectorTabs.forEach((tab) => {{
        tab.addEventListener("click", () => {{
          sectorTabs.forEach((t) => t.classList.remove("active"));
          tab.classList.add("active");
          activeSector = tab.getAttribute("data-sector") || "ALL";
          applyFilters();
        }});
      }});

      searchInput.addEventListener("input", applyFilters);
    }})();
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def portfolio_home(request: Request) -> Response:
    user = _current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return HTMLResponse(
        _render_portfolio_page(user),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


# =============================================================================
# True SSO Agent Workspace Launcher (/launch/{slug}) & Proxy (/app/{slug}/...)
# =============================================================================


@app.get("/launch/{agent_slug}", response_class=HTMLResponse)
async def launch_agent_workspace(request: Request, agent_slug: str) -> Response:
    user = _current_user(request)
    if not user:
        return RedirectResponse(f"/login?next=/launch/{agent_slug}", status_code=302)

    agent = AGENTS_BY_SLUG.get(agent_slug)
    if not agent:
        return RedirectResponse("/", status_code=302)

    # Record lead telemetry for Marketing
    record_agent_launch(
        email=user.get("email", ""),
        agent_slug=agent["slug"],
        agent_title=agent["title"],
    )

    if request.query_params.get("mode") == "direct":
        return RedirectResponse(agent["live_url"], status_code=302)

    title_esc = html.escape(agent["title"])
    sector_esc = html.escape(agent["sector"])
    live_url_esc = html.escape(agent["live_url"])
    user_name_esc = html.escape(str(user.get("name") or user.get("email") or ""))
    user_email_esc = html.escape(str(user.get("email") or ""))
    proxied_entry = f"/app/{agent['slug']}{agent.get('default_path', '/')}"

    workspace_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title_esc} — Sybyl SSO Workspace</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    height: 100%;
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
    background: #0B101E;
  }}
  .sso-shell {{
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100vw;
  }}
  .sso-topbar {{
    height: 48px;
    background: #0B101E;
    color: #FFFFFF;
    border-bottom: 1px solid rgba(255, 255, 255, 0.14);
    padding: 0 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-shrink: 0;
  }}
  .sso-left {{
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }}
  .back-btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 13px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.18);
    color: #FFFFFF;
    font-size: 12.5px;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
  }}
  .back-btn:hover {{
    background: rgba(255, 255, 255, 0.18);
  }}
  .agent-crumb {{
    font-size: 13.5px;
    font-weight: 700;
    color: #FFFFFF;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .sector-crumb {{
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 999px;
    background: rgba(0, 113, 227, 0.28);
    color: #7CC0FF;
    white-space: nowrap;
  }}
  .sso-right {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .sso-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.8);
    white-space: nowrap;
  }}
  .sso-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #30D158;
  }}
  .direct-btn {{
    padding: 6px 12px;
    border-radius: 999px;
    background: #0071E3;
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
  }}
  .sso-frame {{
    flex: 1;
    width: 100%;
    border: none;
    background: #F5F5F7;
  }}
</style>
</head>
<body>
  <div class="sso-shell">
    <header class="sso-topbar">
      <div class="sso-left">
        <a href="/" class="back-btn">← All 61 Agents</a>
        <span class="sector-crumb">{sector_esc}</span>
        <span class="agent-crumb">{title_esc}</span>
      </div>
      <div class="sso-right">
        <span class="sso-pill">
          <span class="sso-dot"></span>
          <span>SSO Active: {user_name_esc} ({user_email_esc})</span>
        </span>
        <a href="{proxied_entry}" target="_blank" rel="noopener" class="back-btn">Full Tab (SSO) ↗</a>
        <a href="{live_url_esc}" target="_blank" rel="noopener" class="direct-btn">Cloud Run Origin ↗</a>
      </div>
    </header>
    <iframe class="sso-frame" src="{proxied_entry}" title="{title_esc}"></iframe>
  </div>
</body>
</html>"""
    return HTMLResponse(workspace_html)


@app.api_route(
    "/app/{agent_slug}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_agent_root(request: Request, agent_slug: str) -> Response:
    return await proxy_agent_subpath(request, agent_slug, "")


@app.api_route(
    "/app/{agent_slug}/{subpath:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_agent_subpath(request: Request, agent_slug: str, subpath: str) -> Response:
    user = _current_user(request)
    if not user:
        return RedirectResponse(f"/login?next=/launch/{agent_slug}", status_code=302)
    agent = AGENTS_BY_SLUG.get(agent_slug)
    if not agent:
        return JSONResponse({"error": f"Unknown agent slug '{agent_slug}'."}, status_code=404)
    return await proxy_agent_request(request, agent, subpath, user)


# =============================================================================
# Marketing Leads & Usage Telemetry Dashboard (/admin & /api/admin/leads.csv)
# =============================================================================


@app.get("/api/admin/telemetry")
async def api_admin_telemetry(request: Request) -> JSONResponse:
    user = _current_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required."}, status_code=401)
    if not is_admin_user(user.get("email", "")):
        return JSONResponse({"error": "Admin access required."}, status_code=403)
    return JSONResponse(get_admin_telemetry())


@app.get("/api/admin/leads.csv")
async def api_admin_leads_csv(request: Request) -> Response:
    user = _current_user(request)
    if not user:
        return RedirectResponse("/login?next=/admin", status_code=302)
    if not is_admin_user(user.get("email", "")):
        return PlainTextResponse("Forbidden: Sybyl staff/admin access required.", status_code=403)

    csv_data = export_leads_csv()
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="sybyl_portfolio_marketing_leads.csv"',
            "Cache-Control": "no-store",
        },
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request) -> Response:
    user = _current_user(request)
    if not user:
        return RedirectResponse("/login?next=/admin", status_code=302)
    if not is_admin_user(user.get("email", "")):
        return HTMLResponse(
            """<!DOCTYPE html><html><body style="font-family:-apple-system,sans-serif;padding:48px;text-align:center;">
            <h2>Restricted to Sybyl Staff &amp; Administrators</h2>
            <p style="color:#515154;margin:12px 0 20px;">Only authorized @sybyl.com team members can view Marketing Leads &amp; Telemetry.</p>
            <a href="/" style="color:#0071E3;font-weight:600;">← Back to Agent Portfolio</a>
            </body></html>""",
            status_code=403,
        )

    telemetry = get_admin_telemetry()

    domain_rows_html: list[str] = []
    for d in telemetry["domains_breakdown"]:
        badge = (
            '<span class="pill pill-staff">Sybyl Staff</span>'
            if d["is_staff"]
            else '<span class="pill pill-lead">B2B Prospect</span>'
        )
        domain_rows_html.append(
            f"""<tr>
              <td><strong>{html.escape(str(d['company']))}</strong></td>
              <td><code>@{html.escape(str(d['domain']))}</code></td>
              <td>{badge}</td>
              <td>{d['leads_count']}</td>
              <td>{d['logins_count']}</td>
              <td>{d['launches_count']}</td>
            </tr>"""
        )

    lead_rows_html: list[str] = []
    for l in telemetry["leads"]:
        provider_pill = (
            '<span class="pill pill-staff">Google SSO</span>'
            if l.get("provider") == "google"
            else '<span class="pill pill-lead">Passwordless OTP</span>'
        )
        agents_list = l.get("agents_launched") or []
        agents_str = (
            ", ".join(html.escape(a) for a in agents_list)
            if agents_list
            else '<span style="color:#86868B;">Browsing directory</span>'
        )
        terms_pill = (
            '<span class="pill pill-staff">Sybyl Staff Policy</span>'
            if l.get("is_staff")
            else '<span class="pill pill-lead">✓ Accepted (v2026.1)</span>'
        )
        lead_rows_html.append(
            f"""<tr>
              <td><strong>{html.escape(str(l.get('name') or ''))}</strong></td>
              <td>{html.escape(str(l.get('company') or ''))}</td>
              <td><a href="mailto:{html.escape(str(l.get('email') or ''))}" style="color:#0071E3;text-decoration:none;">{html.escape(str(l.get('email') or ''))}</a></td>
              <td>{provider_pill}</td>
              <td>{terms_pill}</td>
              <td>{int(l.get('login_count') or 0)}</td>
              <td><strong>{int(l.get('launch_count') or 0)}</strong></td>
              <td style="max-width:280px;font-size:12px;">{agents_str}</td>
              <td style="font-size:12px;color:#515154;">{html.escape(str(l.get('last_seen') or ''))}</td>
            </tr>"""
        )

    admin_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Marketing Leads &amp; Telemetry — Sybyl Enterprise AI Portfolio</title>
<style>
  :root {{
    --bg: #F5F5F7;
    --surface: #FFFFFF;
    --ink: #1D1D1F;
    --ink-secondary: #515154;
    --muted: #86868B;
    --line: #E5E5EA;
    --accent: #0071E3;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
    background: var(--bg);
    color: var(--ink);
    padding-bottom: 60px;
  }}
  .topbar {{
    background: #FFFFFF;
    border-bottom: 1px solid var(--line);
    padding: 16px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }}
  .container {{
    max-width: 1360px;
    margin: 28px auto;
    padding: 0 28px;
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }}
  .kpi-card {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 20px;
  }}
  .kpi-label {{
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    margin-bottom: 6px;
  }}
  .kpi-val {{
    font-size: 28px;
    font-weight: 800;
    color: var(--ink);
  }}
  .panel {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 24px;
    overflow-x: auto;
  }}
  .panel-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    gap: 12px;
    flex-wrap: wrap;
  }}
  .panel-title {{
    font-size: 18px;
    font-weight: 800;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13.5px;
  }}
  th, td {{
    text-align: left;
    padding: 12px 10px;
    border-bottom: 1px solid var(--line);
  }}
  th {{
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
  }}
  .pill {{
    display: inline-block;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 600;
  }}
  .pill-lead {{ background: #EBF7EE; color: #1D7D3F; }}
  .pill-staff {{ background: rgba(0, 113, 227, 0.1); color: #0071E3; }}
  .btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 9px 16px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
  }}
  .btn-primary {{ background: #0071E3; color: #FFFFFF; }}
  .btn-outline {{ border: 1px solid #D2D2D7; color: #1D1D1F; background: #FFFFFF; }}
</style>
</head>
<body>
  <header class="topbar">
    <div style="display:flex;align-items:center;gap:14px;">
      <img src="/Sybyl-Logo.svg" alt="Sybyl" style="height:34px;width:auto;display:block;" />
      <div>
        <h1 style="font-size:19px;font-weight:800;">Marketing Leads &amp; Portfolio Telemetry</h1>
        <div style="font-size:12.5px;color:#515154;">Captured Passwordless Work Email Leads &amp; Sybyl Staff SSO Activity</div>
      </div>
    </div>
    <div style="display:flex;gap:10px;">
      <a href="/api/admin/leads.csv" class="btn btn-primary">⬇ Download Leads CSV</a>
      <a href="/" class="btn btn-outline">← Back to 61 Agents</a>
    </div>
  </header>

  <main class="container">
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Total Captured Users</div>
        <div class="kpi-val">{telemetry['total_users']}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">External B2B Leads</div>
        <div class="kpi-val" style="color:#1D7D3F;">{telemetry['external_leads_count']}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Corporate Domains</div>
        <div class="kpi-val" style="color:#0071E3;">{telemetry['unique_domains_count']}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Total Sign-Ins</div>
        <div class="kpi-val">{telemetry['total_logins']}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Total Agent Launches</div>
        <div class="kpi-val">{telemetry['total_launches']}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">New Leads (Last 7d)</div>
        <div class="kpi-val">{telemetry['new_leads_7d']}</div>
      </div>
    </div>

    <section class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Captured Leads &amp; Activity Directory</h2>
        <a href="/api/admin/leads.csv" class="btn btn-outline">Export CSV</a>
      </div>
      <table>
        <thead>
          <tr>
            <th>Inferred Name</th>
            <th>Company / Domain</th>
            <th>Work Email</th>
            <th>Auth Method</th>
            <th>Legal Terms</th>
            <th>Sign-Ins</th>
            <th>Launches</th>
            <th>Agents Explored</th>
            <th>Last Active (UTC)</th>
          </tr>
        </thead>
        <tbody>
          {''.join(lead_rows_html) if lead_rows_html else '<tr><td colspan="9" style="text-align:center;padding:24px;color:#86868B;">No leads recorded yet.</td></tr>'}
        </tbody>
      </table>
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2 class="panel-title">Organisation &amp; Domain Breakdown</h2>
      </div>
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Domain</th>
            <th>Segment</th>
            <th>Unique Users</th>
            <th>Total Sign-Ins</th>
            <th>Total Agent Launches</th>
          </tr>
        </thead>
        <tbody>
          {''.join(domain_rows_html) if domain_rows_html else '<tr><td colspan="6" style="text-align:center;padding:24px;color:#86868B;">No domains recorded yet.</td></tr>'}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>"""
    return HTMLResponse(admin_html, headers={"Cache-Control": "no-store"})


# Fallback middleware: if an active agent inside /app/{slug} makes a root-relative
# request for /assets/..., /static/..., /_next/..., or /api/... (that isn't one of
# our own portal endpoints), forward it to the active agent's Cloud Run service.
PORTAL_OWN_PREFIXES = (
    "/login",
    "/terms",
    "/Sybyl-Logo.svg",
    "/static/",
    "/auth/",
    "/_health",
    "/api/health",
    "/api/catalog",
    "/api/admin/",
    "/admin",
    "/launch/",
    "/app/",
)


@app.middleware("http")
async def active_agent_asset_fallback(request: Request, call_next):
    path = request.url.path
    if path == "/" or any(path.startswith(p) for p in PORTAL_OWN_PREFIXES):
        return await call_next(request)

    active_slug = request.cookies.get("sybyl_active_agent")
    if active_slug and active_slug in AGENTS_BY_SLUG:
        user = _current_user(request)
        if user:
            return await proxy_agent_request(
                request,
                AGENTS_BY_SLUG[active_slug],
                path.lstrip("/"),
                user,
            )

    return await call_next(request)


# Add SessionMiddleware outermost so request.session is available everywhere
app.add_middleware(
    SessionMiddleware,
    secret_key=get_session_secret(),
    session_cookie="sybyl_portfolio_session",
    max_age=SESSION_MAX_AGE_SECONDS,
    same_site="lax",
    https_only=os.environ.get("HTTPS_ONLY", "0").strip() == "1",
)
