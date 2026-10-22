"""Marketing Lead Capture, Persistence, Telemetry & CSV Export.

Stores B2B leads who sign in via Passwordless Work Email OTP (as well as Sybyl
staff signing in via Google Workspace SSO) in Google Cloud Firestore
(collection ``portfolio_leads`` and ``portfolio_analytics_daily``) with an
automatic local JSON + in-memory fallback.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import io
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

LEADS_COLLECTION = os.environ.get("LEADS_COLLECTION", "portfolio_leads")
ANALYTICS_COLLECTION = os.environ.get("ANALYTICS_COLLECTION", "portfolio_analytics_daily")
LOCAL_LEADS_PATH = Path(os.environ.get("LOCAL_LEADS_PATH", "/tmp/sybyl_portfolio_leads.json"))

_MEM_LEADS: dict[str, dict[str, Any]] = {}
_MEM_DAILY: dict[str, dict[str, Any]] = {}

_FS_CLIENT = None
_FS_INIT_TRIED = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_key() -> str:
    return _utc_now().strftime("%Y-%m-%d")


def _get_firestore():
    global _FS_CLIENT, _FS_INIT_TRIED
    if _FS_INIT_TRIED:
        return _FS_CLIENT
    _FS_INIT_TRIED = True
    if os.environ.get("LEADS_FORCE_MEMORY", "").strip().lower() in ("1", "true", "yes"):
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
        logger.warning("Firestore unavailable for leads store (%s); using local store.", exc)
        _FS_CLIENT = None
        return None


def _load_local_cache() -> None:
    if _MEM_LEADS:
        return
    if LOCAL_LEADS_PATH.exists():
        try:
            raw = json.loads(LOCAL_LEADS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k, v in raw.get("leads", {}).items():
                    _MEM_LEADS[k] = v
                for k, v in raw.get("daily", {}).items():
                    _MEM_DAILY[k] = v
        except Exception as exc:
            logger.warning("Failed to read local leads file (%s)", exc)


def _save_local_cache() -> None:
    try:
        LOCAL_LEADS_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_LEADS_PATH.write_text(
            json.dumps({"leads": _MEM_LEADS, "daily": _MEM_DAILY}, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Failed to write local leads file (%s)", exc)


def infer_company_from_domain(domain: str) -> str:
    if not domain:
        return ""
    part = domain.split(".")[0].replace("-", " ").replace("_", " ").strip()
    if not part:
        return domain
    if part.lower() == "sybyl":
        return "Sybyl"
    return part.title()


def infer_name_from_email(email: str) -> str:
    local = (email or "").split("@")[0]
    cleaned = local.replace(".", " ").replace("_", " ").replace("-", " ").strip()
    return cleaned.title() if cleaned else email


def record_lead_login(
    email: str,
    name: str = "",
    company: str = "",
    role: str = "",
    provider: str = "email_otp",
    picture: str = "",
    client_ip: str = "",
    terms_accepted: bool = True,
    terms_version: str = "2026.1",
) -> dict[str, Any]:
    """Create or update a lead record upon successful authentication."""
    _load_local_cache()
    email_clean = (email or "").strip().lower()
    if not email_clean or "@" not in email_clean:
        return {}

    domain = email_clean.split("@", 1)[1].strip().lower()
    now_iso = _utc_now_iso()
    today = _today_key()

    existing: dict[str, Any] = dict(_MEM_LEADS.get(email_clean, {}))
    db = _get_firestore()
    if db is not None:
        try:
            snap = db.collection(LEADS_COLLECTION).document(email_clean).get()
            if snap.exists:
                fs_data = snap.to_dict() or {}
                existing = {**existing, **fs_data}
        except Exception as exc:
            logger.warning("Firestore lead read failed (%s).", exc)

    resolved_name = (
        name.strip()
        or str(existing.get("name") or "").strip()
        or infer_name_from_email(email_clean)
    )
    resolved_company = (
        company.strip()
        or str(existing.get("company") or "").strip()
        or infer_company_from_domain(domain)
    )
    resolved_role = (
        role.strip()
        or str(existing.get("role") or "").strip()
        or ("Sybyl Staff" if domain == "sybyl.com" else "Business Leader")
    )

    is_staff = domain == "sybyl.com"
    first_seen = str(existing.get("first_seen") or now_iso)
    login_count = int(existing.get("login_count") or 0) + 1
    launch_count = int(existing.get("launch_count") or 0)
    agents_launched = list(existing.get("agents_launched") or [])
    terms_accepted_at = str(existing.get("terms_accepted_at") or now_iso)

    record: dict[str, Any] = {
        "email": email_clean,
        "name": resolved_name,
        "company": resolved_company,
        "role": resolved_role,
        "domain": domain,
        "provider": provider,
        "is_staff": is_staff,
        "picture": picture or str(existing.get("picture") or ""),
        "first_seen": first_seen,
        "last_seen": now_iso,
        "login_count": login_count,
        "launch_count": launch_count,
        "agents_launched": agents_launched,
        "last_agent_launched": str(existing.get("last_agent_launched") or ""),
        "last_launch_at": str(existing.get("last_launch_at") or ""),
        "client_ip": client_ip or str(existing.get("client_ip") or ""),
        "terms_accepted": bool(terms_accepted or is_staff or existing.get("terms_accepted")),
        "terms_version": terms_version,
        "terms_accepted_at": terms_accepted_at,
    }

    _MEM_LEADS[email_clean] = record

    daily = dict(_MEM_DAILY.get(today, {"date": today, "logins_total": 0, "logins_otp": 0, "logins_google": 0, "launches_total": 0}))
    daily["logins_total"] = int(daily.get("logins_total", 0)) + 1
    if provider == "google":
        daily["logins_google"] = int(daily.get("logins_google", 0)) + 1
    else:
        daily["logins_otp"] = int(daily.get("logins_otp", 0)) + 1
    _MEM_DAILY[today] = daily
    _save_local_cache()

    if db is not None:
        try:
            db.collection(LEADS_COLLECTION).document(email_clean).set(record, merge=True)
            from google.cloud import firestore  # type: ignore

            inc_field = "logins_google" if provider == "google" else "logins_otp"
            db.collection(ANALYTICS_COLLECTION).document(today).set(
                {
                    "date": today,
                    "logins_total": firestore.Increment(1),
                    inc_field: firestore.Increment(1),
                    "updated_at": now_iso,
                },
                merge=True,
            )
        except Exception as exc:
            logger.warning("Firestore lead write failed (%s).", exc)

    return record


def record_agent_launch(email: str, agent_slug: str, agent_title: str) -> dict[str, Any]:
    """Record that an authenticated user launched a specific agent from the portfolio."""
    _load_local_cache()
    email_clean = (email or "").strip().lower()
    if not email_clean:
        return {}

    now_iso = _utc_now_iso()
    today = _today_key()

    existing: dict[str, Any] = dict(_MEM_LEADS.get(email_clean, {}))
    db = _get_firestore()
    if db is not None:
        try:
            snap = db.collection(LEADS_COLLECTION).document(email_clean).get()
            if snap.exists:
                fs_data = snap.to_dict() or {}
                existing = {**existing, **fs_data}
        except Exception as exc:
            logger.warning("Firestore lead read on launch failed (%s).", exc)

    if not existing:
        existing = record_lead_login(email=email_clean)

    agents_launched: list[str] = list(existing.get("agents_launched") or [])
    if agent_title and agent_title not in agents_launched:
        agents_launched.append(agent_title)

    existing["launch_count"] = int(existing.get("launch_count") or 0) + 1
    existing["agents_launched"] = agents_launched
    existing["last_agent_launched"] = agent_title
    existing["last_launch_at"] = now_iso
    existing["last_seen"] = now_iso

    _MEM_LEADS[email_clean] = existing

    daily = dict(_MEM_DAILY.get(today, {"date": today, "logins_total": 0, "logins_otp": 0, "logins_google": 0, "launches_total": 0}))
    daily["launches_total"] = int(daily.get("launches_total", 0)) + 1
    _MEM_DAILY[today] = daily
    _save_local_cache()

    if db is not None:
        try:
            db.collection(LEADS_COLLECTION).document(email_clean).set(existing, merge=True)
            from google.cloud import firestore  # type: ignore

            db.collection(ANALYTICS_COLLECTION).document(today).set(
                {
                    "date": today,
                    "launches_total": firestore.Increment(1),
                    f"agent_launches.{agent_slug}": firestore.Increment(1),
                    "updated_at": now_iso,
                },
                merge=True,
            )
        except Exception as exc:
            logger.warning("Firestore launch write failed (%s).", exc)

    return existing


def list_all_leads() -> list[dict[str, Any]]:
    """Return all captured leads sorted by most recently active."""
    _load_local_cache()
    merged: dict[str, dict[str, Any]] = {k: dict(v) for k, v in _MEM_LEADS.items()}

    db = _get_firestore()
    if db is not None:
        try:
            for snap in db.collection(LEADS_COLLECTION).stream():
                data = snap.to_dict() or {}
                email_key = str(data.get("email") or snap.id).strip().lower()
                if email_key:
                    merged[email_key] = {**merged.get(email_key, {}), **data}
        except Exception as exc:
            logger.warning("Firestore list_all_leads failed (%s).", exc)

    items = list(merged.values())
    items.sort(key=lambda r: str(r.get("last_seen") or ""), reverse=True)
    return items


def get_admin_telemetry() -> dict[str, Any]:
    """Compute KPIs, domain breakdown, and lead table for the Marketing & Admin dashboard."""
    leads = list_all_leads()
    now = _utc_now()
    cutoff_7d = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cutoff_30d = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    external_leads = [l for l in leads if not l.get("is_staff")]
    staff_users = [l for l in leads if l.get("is_staff")]

    total_logins = sum(int(l.get("login_count") or 0) for l in leads)
    total_launches = sum(int(l.get("launch_count") or 0) for l in leads)
    new_7d = sum(1 for l in leads if str(l.get("first_seen") or "") >= cutoff_7d)
    new_30d = sum(1 for l in leads if str(l.get("first_seen") or "") >= cutoff_30d)
    active_7d = sum(1 for l in leads if str(l.get("last_seen") or "") >= cutoff_7d)

    domains_map: dict[str, dict[str, Any]] = {}
    for l in leads:
        dom = str(l.get("domain") or "unknown").lower()
        entry = domains_map.setdefault(
            dom,
            {
                "domain": dom,
                "company": str(l.get("company") or infer_company_from_domain(dom)),
                "leads_count": 0,
                "logins_count": 0,
                "launches_count": 0,
                "is_staff": dom == "sybyl.com",
            },
        )
        entry["leads_count"] += 1
        entry["logins_count"] += int(l.get("login_count") or 0)
        entry["launches_count"] += int(l.get("launch_count") or 0)

    domains_breakdown = sorted(
        domains_map.values(),
        key=lambda d: (not d["is_staff"], d["leads_count"], d["launches_count"]),
        reverse=True,
    )

    return {
        "total_users": len(leads),
        "external_leads_count": len(external_leads),
        "staff_users_count": len(staff_users),
        "unique_domains_count": len(domains_map),
        "external_domains_count": sum(1 for d in domains_map.values() if not d["is_staff"]),
        "total_logins": total_logins,
        "total_launches": total_launches,
        "new_leads_7d": new_7d,
        "new_leads_30d": new_30d,
        "active_users_7d": active_7d,
        "domains_breakdown": domains_breakdown,
        "leads": leads,
    }


def export_leads_csv() -> str:
    """Serialize all captured leads to a Marketing-ready CSV string."""
    leads = list_all_leads()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Full Name",
            "Company",
            "Job Title / Role",
            "Work Email",
            "Business Domain",
            "Lead Type",
            "Sign-In Method",
            "Terms Accepted",
            "Terms Accepted At (UTC)",
            "Login Count",
            "Agent Launches",
            "Agents Explored",
            "Last Agent Launched",
            "First Seen (UTC)",
            "Last Seen (UTC)",
        ]
    )
    for l in leads:
        writer.writerow(
            [
                l.get("name", ""),
                l.get("company", ""),
                l.get("role", ""),
                l.get("email", ""),
                l.get("domain", ""),
                "Sybyl Staff" if l.get("is_staff") else "External Prospect / Lead",
                "Google Workspace SSO" if l.get("provider") == "google" else "Passwordless Work Email OTP",
                "Sybyl Staff Policy" if l.get("is_staff") else ("Accepted (v2026.1)" if l.get("terms_accepted", True) else "No"),
                l.get("terms_accepted_at") or l.get("first_seen", ""),
                l.get("login_count", 0),
                l.get("launch_count", 0),
                " | ".join(l.get("agents_launched") or []),
                l.get("last_agent_launched", ""),
                l.get("first_seen", ""),
                l.get("last_seen", ""),
            ]
        )
    return buf.getvalue()


def reset_leads_for_tests() -> None:
    """Clear in-memory and local JSON lead cache (used by automated test suites)."""
    _MEM_LEADS.clear()
    _MEM_DAILY.clear()
    if LOCAL_LEADS_PATH.exists():
        try:
            LOCAL_LEADS_PATH.unlink()
        except Exception:
            pass
