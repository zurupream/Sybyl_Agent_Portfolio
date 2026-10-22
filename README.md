# Sybyl Agentic AI Portfolio & Single Sign-On Portal

Unified Single Sign-On (SSO) and Marketing Lead-Generation Web Portal for the **Sybyl Agentic AI Portfolio** (**61 deployed agents across 8 enterprise sectors**), built on Gemini Enterprise concepts (Gemini models, Google Agent Development Kit, Cloud Run on Google Cloud).

## Key Features

1. **Page 1 — Single Sign-On & Lead Capture (`/login`)**
   - **Primary Option (Passwordless Work Email Sign-In for Lead Generation):** Captures **Full Name, Company / Organisation, Job Title / Role, and Work Email** (`name@company.com`), blocks personal/free consumer domains (`gmail.com`, `yahoo.com`, `outlook.com`, `hotmail.com`, `icloud.com`, etc.) and disposable addresses, and sends a 6-digit one-time verification code via Google Workspace SMTP.
   - **Secondary Option (Sybyl Staff Google Sign-In):** 1-click Google Workspace Sign-In (`@sybyl.com` and explicitly allowlisted emails).

2. **Page 2 — Enterprise Agentic AI Portfolio Directory (`/`)**
   - Interactive catalog of **61 deployed agents across 8 sectors**:
     - **Banking & Financial Services** (12)
     - **Public Sector** (11)
     - **Insurance** (12)
     - **Sales & Distribution** (6)
     - **Finance Reconciliation** (4)
     - **Retail Operations** (3)
     - **Manufacturing & Executive Data** (4)
     - **Human Resources** (9)
   - Displays **Design Principles**, real-time search across titles, capabilities, and business value, sector filter tabs, and 1-click **Launch Agent (SSO)**.

3. **True Single Sign-On Handoff (`/launch/{slug}` & `/app/{slug}/...`)**
   - Automatically seeds downstream agent sessions (both signed Starlette `session` cookies and browser `localStorage`/`sessionStorage` keys across all 61 agents) so authenticated users launch straight into any agent workspace without signing in a second time.

4. **Marketing Leads & Telemetry Dashboard (`/admin` & `/api/admin/leads.csv`)**
   - Captures every sign-in and agent launch in Google Cloud Firestore (`portfolio_leads` & `portfolio_analytics_daily`) and provides a real-time lead table + 1-click CSV export for the Marketing team.
