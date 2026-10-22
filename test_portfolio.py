import os
import re

os.environ["OTP_TEST_MODE"] = "1"
os.environ["OTP_FORCE_MEMORY"] = "1"
os.environ["LEADS_FORCE_MEMORY"] = "1"
os.environ["OPEN_BUSINESS_SIGNUP"] = "1"
os.environ["ALLOWED_DOMAINS"] = "sybyl.com,kimisitusacco.or.ke"
os.environ["ALLOWED_EMAILS"] = "zuruprem@gmail.com,guruprem.saginadham@sybyl.com"
os.environ["ADMIN_EMAILS"] = "zuruprem@gmail.com,guruprem.saginadham@sybyl.com"
os.environ["SESSION_SECRET"] = "test-session-secret-for-portfolio"

from fastapi.testclient import TestClient

import catalog
import leads
import mail
import otp
import sso_gateway
from main import app


def test_catalog_counts_and_strict_exclusions():
    summary = catalog.get_catalog_summary()
    assert summary["total_agents"] == 61
    assert summary["total_sectors"] == 8

    expected_counts = {
        "banking-financial-services": 12,
        "public-sector": 11,
        "insurance": 12,
        "sales-distribution": 6,
        "finance-reconciliation": 4,
        "retail-operations": 3,
        "manufacturing-executive-data": 4,
        "human-resources": 9,
    }
    actual_counts = {s["slug"]: s["count"] for s in summary["sectors"]}
    assert actual_counts == expected_counts

    forbidden_a = "ka" + "ren"
    forbidden_b = "ro" + "ses"
    for agent in catalog.AGENTS_CATALOG:
        blob = f"{agent['slug']} {agent['title']} {agent['what_it_does']} {agent['value']} {agent['live_url']}".lower()
        assert forbidden_a not in blob, f"Forbidden client reference found in {agent['slug']}"
        assert forbidden_b not in blob, f"Forbidden client reference found in {agent['slug']}"
        assert "copilot" not in blob, f"Forbidden 'copilot' term found in {agent['slug']}"


def test_unauthenticated_redirects_to_login():
    client = TestClient(app)
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/login"

    login_res = client.get("/login")
    assert login_res.status_code == 200
    assert "Passwordless Work Email" in login_res.text
    assert "Sybyl Staff" in login_res.text
    assert "61" in login_res.text
    assert 'id="lead-email"' in login_res.text
    assert 'id="terms-checkbox"' in login_res.text
    assert "Use-at-Your-Own-Risk Disclaimer" in login_res.text
    assert "/Sybyl-Logo.svg" in login_res.text
    assert 'id="lead-name"' not in login_res.text
    assert 'id="lead-role"' not in login_res.text

    logo_res = client.get("/Sybyl-Logo.svg")
    assert logo_res.status_code == 200
    assert "image/svg+xml" in logo_res.headers.get("content-type", "")
    assert "<svg" in logo_res.text
    assert "#ea0029" in logo_res.text
    assert ("ka" + "ren") not in login_res.text.lower()

    terms_res = client.get("/terms")
    assert terms_res.status_code == 200
    assert "No Account Creation &amp; Business Email-Only Capture" in terms_res.text
    assert "Corporate Google Gemini Enterprise Safeguards" in terms_res.text
    assert "never used to train" in terms_res.text
    assert "AI Can Make Mistakes" in terms_res.text
    assert "Use at Your Own Risk" in terms_res.text


def test_consumer_and_disposable_domains_blocked():
    client = TestClient(app)

    for blocked_email in [
        "random.person@gmail.com",
        "john.doe@yahoo.com",
        "jane.doe@outlook.com",
        "test.user@hotmail.com",
        "temp.user@mailinator.com",
    ]:
        res = client.post(
            "/auth/email/send-otp",
            json={
                "email": blocked_email,
                "name": "Test User",
                "company": "Personal",
                "role": "Individual",
            },
        )
        assert res.status_code == 403, f"Expected 403 for {blocked_email}, got {res.status_code}"


def test_full_passwordless_lead_capture_and_portfolio_access():
    otp._MEM_CODES.clear()
    otp._MEM_RATES.clear()
    leads.reset_leads_for_tests()
    mail.clear_test_outbox()

    client = TestClient(app)

    # 1a. Non-Sybyl visitor MUST accept Terms & Conditions (rejected with 400 if terms_accepted=False)
    missing_terms_res = client.post(
        "/auth/email/send-otp",
        json={
            "email": "jane.muthoni@equitybank.co.ke",
            "terms_accepted": False,
        },
    )
    assert missing_terms_res.status_code == 400
    assert "Terms & Conditions" in missing_terms_res.json()["error"]

    # 1b. Request OTP with ONLY business work email + terms_accepted=True
    send_res = client.post(
        "/auth/email/send-otp",
        json={
            "email": "jane.muthoni@equitybank.co.ke",
            "terms_accepted": True,
        },
    )
    assert send_res.status_code == 200
    data = send_res.json()
    assert data["ok"] is True

    outbox = mail.get_test_outbox()
    assert len(outbox) == 1
    assert outbox[0]["to"] == "jane.muthoni@equitybank.co.ke"
    code = outbox[0]["code"]
    assert re.fullmatch(r"\d{6}", code)

    # 2. Verify OTP with ONLY email + 6-digit code
    verify_res = client.post(
        "/auth/email/verify-otp",
        json={
            "email": "jane.muthoni@equitybank.co.ke",
            "code": code,
        },
    )
    assert verify_res.status_code == 200
    vdata = verify_res.json()
    assert vdata["ok"] is True
    assert vdata["user"]["email"] == "jane.muthoni@equitybank.co.ke"
    assert vdata["user"]["name"] == "Jane Muthoni"
    assert vdata["user"]["company"] == "Equitybank"

    # 3. Access Portfolio Directory (/)
    home_res = client.get("/")
    assert home_res.status_code == 200
    html = home_res.text
    assert "Jane Muthoni" in html
    assert "Bank Statement Analyzer" in html
    assert "Enterprise Contracts Analyzer" in html
    assert "Learning, Certification Expiry &amp; Skills Matrix Agent" in html
    assert ("ka" + "ren") not in html.lower()

    # Check all 61 agent launch links appear in the rendered directory
    for agent in catalog.AGENTS_CATALOG:
        assert f'/launch/{agent["slug"]}' in html

    # 4. Launch an agent via SSO gateway
    launch_res = client.get("/launch/bank-statement-analyzer", follow_redirects=False)
    assert launch_res.status_code == 200
    assert "/app/bank-statement-analyzer" in launch_res.text
    assert "SSO Active: Jane Muthoni" in launch_res.text


def test_sso_html_rewriting_injects_session_keys():
    agent = catalog.AGENTS_BY_SLUG["bank-statement-analyzer"]
    sample_html = '<!DOCTYPE html><html><head><title>Bank Statement Analyzer</title><link rel="stylesheet" href="/static/style.css"></head><body><h1>App</h1></body></html>'
    user = {
        "email": "jane.muthoni@equitybank.co.ke",
        "name": "Jane Muthoni",
        "company": "Equity Bank Kenya",
        "role": "Director of Credit Underwriting",
        "provider": "email_otp",
    }
    rewritten = sso_gateway.rewrite_html_for_sso(sample_html, user, agent)
    assert 'href="/app/bank-statement-analyzer/static/style.css"' in rewritten
    assert "banking_rm_user" in rewritten
    assert "cam_authenticated_user" in rewritten
    assert "jane.muthoni@equitybank.co.ke" in rewritten
    assert 'data-sybyl-sso="1"' in rewritten


def test_admin_lead_telemetry_and_csv_export():
    otp._MEM_CODES.clear()
    otp._MEM_RATES.clear()
    mail.clear_test_outbox()

    client = TestClient(app)

    # Sign in as allowlisted admin (zuruprem@gmail.com)
    send_res = client.post(
        "/auth/email/send-otp",
        json={
            "email": "zuruprem@gmail.com",
            "terms_accepted": True,
        },
    )
    assert send_res.status_code == 200
    code = mail.get_test_outbox()[-1]["code"]

    verify_res = client.post(
        "/auth/email/verify-otp",
        json={
            "email": "zuruprem@gmail.com",
            "code": code,
        },
    )
    assert verify_res.status_code == 200

    # Check JSON telemetry
    tel_res = client.get("/api/admin/telemetry")
    assert tel_res.status_code == 200
    tdata = tel_res.json()
    assert tdata["total_users"] >= 2
    assert tdata["external_leads_count"] >= 1
    emails = [lead["email"] for lead in tdata["leads"]]
    assert "jane.muthoni@equitybank.co.ke" in emails
    assert "zuruprem@gmail.com" in emails

    # Check Admin HTML page
    admin_res = client.get("/admin")
    assert admin_res.status_code == 200
    assert "Marketing Leads &amp; Portfolio Telemetry" in admin_res.text
    assert "jane.muthoni@equitybank.co.ke" in admin_res.text
    assert "equitybank.co.ke" in admin_res.text

    # Check CSV export
    csv_res = client.get("/api/admin/leads.csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "jane.muthoni@equitybank.co.ke" in csv_res.text
    assert "equitybank.co.ke" in csv_res.text
    assert "Bank Statement Analyzer" in csv_res.text
