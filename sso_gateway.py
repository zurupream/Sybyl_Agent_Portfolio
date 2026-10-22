"""True Single Sign-On (SSO) Gateway & Reverse Proxy for all 61 Sybyl Agents.

Ensures that once a user authenticates once on the Sybyl AI Portfolio portal
(either via Passwordless Work Email OTP or Sybyl Staff Google Sign-In),
launching any agent opens the authenticated workbench directly without a
second sign-in prompt.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from auth import create_starlette_session_cookie_value

logger = logging.getLogger(__name__)

# Complete registry of localStorage / sessionStorage keys used across all SPA agents
SSO_STORAGE_KEYS: list[str] = [
    "alco_treasury_auth_user_v1",
    "ap_recon_user",
    "banking_aida_session_user_v1",
    "banking_card_dispute_sso_user",
    "banking_rm_user",
    "bom_yield_agent_user",
    "broker_quote_comparison_auth_user",
    "cam_authenticated_user",
    "clara_auth_user",
    "comp_price_agent_user",
    "edms_catalogue_agent_user_v1",
    "edunexus_user",
    "factory_machine_repair_guide_user_v2",
    "fefo_agent_user",
    "finance_cashapp_agent06_user",
    "hr_attendance_leave_agent06_user",
    "hr_helpdesk_agent_user_v1",
    "hr_offboarding_user",
    "hr_onboarding_sso_session",
    "hr_payroll_recon_agent05_user",
    "hr_skills_agent_user",
    "hr_workforce_agent_user",
    "insurance_group_census_auth_user",
    "insurance_loss_ratio_auth_user",
    "insurance_policy_wording_auth_user",
    "iqc_coa_user",
    "kam_agent_user",
    "loan_review_agent_user",
    "media_digest_auth_user",
    "medical_bill_scrubber_auth_user",
    "motor_valuation_auth_user",
    "onboarding_prep_agent_user",
    "overdraft_renewal_auth_user",
    "pod_agent_user",
    "policy_comparison_user",
    "pos_recon_user",
    "property_risk_survey_auth_user",
    "reinsurance_fac_auth_user",
    "retail_reorder_agent_user_v1",
    "retail_returns_warranty_agent_user_v2",
    "scheduler_active_session",
    "sybyl_crop_auth_user",
    "sybyl_exec_sop_agent_user_v1",
    "sybyl_sentinel_auth_user",
    "trade_lc_agent_user_session_v1",
]

HOP_BY_HOP_HEADERS: frozenset[str] = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "content-encoding",
        "content-length",
        "x-frame-options",
        "content-security-policy",
        "content-security-policy-report-only",
    }
)


def get_upstream_base_url(agent: dict[str, Any]) -> str:
    """Return the scheme + netloc origin of an agent's live_url."""
    parsed = urlparse(agent["live_url"])
    return f"{parsed.scheme}://{parsed.netloc}"


def build_sso_injection_script(user: dict[str, Any], agent: dict[str, Any]) -> str:
    """Build the early-<head> JavaScript snippet that seeds SSO state and routes API calls."""
    profile = {
        "email": user.get("email", "guest@enterprise.com"),
        "name": user.get("name") or user.get("email", "Enterprise User"),
        "company": user.get("company") or "Enterprise",
        "role": user.get("role") or "Business User",
        "picture": user.get("picture") or "",
        "provider": user.get("provider") or "email_otp",
        "authenticated": True,
        "is_admin": bool(user.get("is_admin", False)),
    }
    slug = agent["slug"]
    prefix = f"/app/{slug}"
    keys_json = json.dumps(SSO_STORAGE_KEYS)
    profile_json = json.dumps(profile)

    return f"""<script data-sybyl-sso="1">
(function() {{
  try {{
    var userProfile = {profile_json};
    var profileStr = JSON.stringify(userProfile);
    var storageKeys = {keys_json};
    for (var i = 0; i < storageKeys.length; i++) {{
      try {{
        window.localStorage.setItem(storageKeys[i], profileStr);
        window.sessionStorage.setItem(storageKeys[i], profileStr);
      }} catch (_) {{}}
    }}
    window.localStorage.setItem("sybyl_sso_user", profileStr);
    window.localStorage.setItem("sybyl_portal_authenticated", "true");
    window.localStorage.setItem("supplier_prequal_portal_authenticated", "true");
    if (!window.sessionStorage.getItem("hr_google_id_token")) {{
      window.sessionStorage.setItem("hr_google_id_token", "demo-token:" + userProfile.email);
    }}
    window.__SYBYL_SSO_USER__ = userProfile;
  }} catch (e) {{}}

  var prefix = {json.dumps(prefix)};
  function rewriteUrl(u) {{
    if (typeof u !== "string") return u;
    if (u.startsWith(prefix + "/") || u === prefix) return u;
    if (u.startsWith("/auth/") || u.startsWith("/launch/") || u.startsWith("/app/")) return u;
    if (u.startsWith("/") && !u.startsWith("//")) {{
      return prefix + u;
    }}
    return u;
  }}

  var origFetch = window.fetch;
  if (origFetch) {{
    window.fetch = function(input, init) {{
      if (typeof input === "string") {{
        input = rewriteUrl(input);
      }} else if (input && typeof input.url === "string" && input instanceof Request) {{
        try {{
          var locOrigin = window.location.origin;
          if (input.url.startsWith(locOrigin + "/")) {{
            var rel = input.url.slice(locOrigin.length);
            var rewritten = rewriteUrl(rel);
            if (rewritten !== rel) {{
              input = new Request(locOrigin + rewritten, input);
            }}
          }}
        }} catch (_) {{}}
      }}
      return origFetch.call(this, input, init);
    }};
  }}

  if (window.XMLHttpRequest && window.XMLHttpRequest.prototype) {{
    var origOpen = window.XMLHttpRequest.prototype.open;
    window.XMLHttpRequest.prototype.open = function(method, url) {{
      var args = Array.prototype.slice.call(arguments);
      if (typeof args[1] === "string") {{
        args[1] = rewriteUrl(args[1]);
      }}
      return origOpen.apply(this, args);
    }};
  }}
}})();
</script>"""


_ATTR_RE = re.compile(
    r'(\b(?:src|href|action)\s*=\s*["\'])(/(?!app/|launch/|auth/|/)[^"\']*)(["\'])',
    re.IGNORECASE,
)


def rewrite_html_for_sso(html_text: str, user: dict[str, Any], agent: dict[str, Any]) -> str:
    """Inject SSO pre-seeding script and rewrite root-relative asset paths for ``agent``."""
    slug = agent["slug"]
    prefix = f"/app/{slug}"

    rewritten = _ATTR_RE.sub(rf"\1{prefix}\2\3", html_text)
    sso_script = build_sso_injection_script(user, agent)

    if re.search(r"<head[^>]*>", rewritten, re.IGNORECASE):
        rewritten = re.sub(
            r"(<head[^>]*>)",
             lambda m: m.group(1) + "\n" + sso_script,
            rewritten,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        rewritten = sso_script + "\n" + rewritten

    return rewritten


async def proxy_agent_request(
    request: Request,
    agent: dict[str, Any],
    subpath: str,
    user: dict[str, Any],
) -> Response:
    """Reverse-proxy a request to the target agent's Cloud Run origin with SSO injection."""
    base_origin = get_upstream_base_url(agent)
    normalized_subpath = subpath.lstrip("/")
    if not normalized_subpath and agent.get("default_path") and agent["default_path"] != "/":
        default_target = f"/app/{agent['slug']}{agent['default_path']}"
        return RedirectResponse(default_target, status_code=302)

    target_url = urljoin(base_origin + "/", normalized_subpath)
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # Build upstream headers
    fwd_headers: dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in ("host", "content-length", "accept-encoding"):
            continue
        fwd_headers[k] = v

    # Attach enterprise SSO identity headers + signed Starlette session cookie
    email = user.get("email", "guest@enterprise.com")
    fwd_headers["X-Goog-Authenticated-User-Email"] = f"accounts.google.com:{email}"
    fwd_headers["X-Sybyl-SSO-User"] = json.dumps(
        {
            "email": email,
            "name": user.get("name", ""),
            "company": user.get("company", ""),
            "role": user.get("role", ""),
            "provider": user.get("provider", "email_otp"),
        }
    )

    signed_session = create_starlette_session_cookie_value(
        {
            "user": {
                "email": email,
                "name": user.get("name") or email,
                "picture": user.get("picture") or "",
                "hd": email.split("@")[-1] if "@" in email else "",
                "sub": f"sso:{email}",
                "provider": user.get("provider") or "email_otp",
                "iat": user.get("iat") or 1700000000,
                "exp": (user.get("exp") or 1900000000),
            }
        }
    )
    existing_cookie = fwd_headers.get("cookie") or fwd_headers.get("Cookie") or ""
    if existing_cookie:
        fwd_headers["Cookie"] = f"{existing_cookie}; session={signed_session}"
    else:
        fwd_headers["Cookie"] = f"session={signed_session}"

    body_bytes = await request.body()

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            upstream_resp = await client.request(
                method=request.method,
                url=target_url,
                headers=fwd_headers,
                content=body_bytes if body_bytes else None,
            )
    except Exception as exc:
        logger.warning("Upstream proxy error for %s (%s): %s", agent["slug"], target_url, exc)
        return HTMLResponse(
            f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{agent['title']}</title></head>
<body style="font-family:-apple-system,sans-serif;padding:40px;background:#F5F5F7;color:#1D1D1F;text-align:center;">
  <div style="max-width:520px;margin:60px auto;background:#FFF;padding:32px;border-radius:18px;border:1px solid #E5E5EA;">
    <h2 style="margin:0 0 12px;">Connecting to {agent['title']}</h2>
    <p style="color:#515154;font-size:14px;line-height:1.5;margin-bottom:20px;">
      The agent container is waking up or temporarily unreachable via the embedded gateway. You can open the live Cloud Run service directly below:
    </p>
    <a href="{agent['live_url']}" target="_blank" rel="noopener"
       style="display:inline-block;padding:12px 24px;background:#0071E3;color:#FFF;text-decoration:none;border-radius:999px;font-weight:600;font-size:14px;">
      Open {agent['title']} Directly ↗
    </a>
  </div>
</body></html>""",
            status_code=502,
        )

    resp_headers: dict[str, str] = {}
    for k, v in upstream_resp.headers.items():
        if k.lower() not in HOP_BY_HOP_HEADERS:
            resp_headers[k] = v

    content_type = upstream_resp.headers.get("content-type", "").lower()
    if "text/html" in content_type:
        html_text = upstream_resp.text
        patched_html = rewrite_html_for_sso(html_text, user, agent)
        response = HTMLResponse(
            content=patched_html,
            status_code=upstream_resp.status_code,
            headers=resp_headers,
        )
    else:
        response = Response(
            content=upstream_resp.content,
            status_code=upstream_resp.status_code,
            headers=resp_headers,
            media_type=upstream_resp.headers.get("content-type"),
        )

    response.set_cookie(
        "sybyl_active_agent",
        agent["slug"],
        max_age=3600 * 8,
        path="/",
        httponly=False,
        samesite="lax",
    )
    return response
