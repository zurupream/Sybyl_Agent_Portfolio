"""Complete catalog of the 61 Sybyl Enterprise AI Agents across 8 sectors.

Strictly excludes customer-specific private deployments.
"""

from __future__ import annotations

from typing import Any

DESIGN_PRINCIPLES: list[dict[str, str]] = [
    {
        "title": "Reasoning + Deterministic Python",
        "description": (
            "The model does reasoning and document reading; deterministic Python "
            "does calculations, rules and validation."
        ),
        "icon": "cpu",
    },
    {
        "title": "Human-in-the-Loop Governance",
        "description": (
            "A human approves before anything is posted, sent or paid."
        ),
        "icon": "user-check",
    },
    {
        "title": "Enterprise Single Sign-On",
        "description": (
            "Enterprise sign-in on every agent — sign in once on this portal "
            "to launch any agent across all 8 industry sectors."
        ),
        "icon": "shield-check",
    },
]

SECTORS_ORDER: list[dict[str, Any]] = [
    {
        "name": "Banking & Financial Services",
        "slug": "banking-financial-services",
        "expected_count": 12,
        "icon": "landmark",
        "accent": "#0071E3",
        "tagline": "Underwriting, cash-flow spreading, relationship insights, collections, trade finance & ALCO stress testing.",
    },
    {
        "name": "Public Sector",
        "slug": "public-sector",
        "expected_count": 11,
        "icon": "building-2",
        "accent": "#1D7D3F",
        "tagline": "Contract review, credential verification, IT triage, procurement prequalification & citizen services.",
    },
    {
        "name": "Insurance",
        "slug": "insurance",
        "expected_count": 12,
        "icon": "umbrella",
        "accent": "#5E5CE6",
        "tagline": "Motor renewals, multimodal claims vetting, medical bill scrubbing, quote comparisons & treaty capacity.",
    },
    {
        "name": "Sales & Distribution",
        "slug": "sales-distribution",
        "expected_count": 6,
        "icon": "truck",
        "accent": "#D95F02",
        "tagline": "PO-to-sales-order resolution, proof-of-delivery credit notes, key account health & outbound outreach.",
    },
    {
        "name": "Finance Reconciliation",
        "slug": "finance-reconciliation",
        "expected_count": 4,
        "icon": "calculator",
        "accent": "#0A7B83",
        "tagline": "Three-way invoice matching, cash allocation, 4-way retail POS tender settlement & supplier statements.",
    },
    {
        "name": "Retail Operations",
        "slug": "retail-operations",
        "expected_count": 3,
        "icon": "shopping-bag",
        "accent": "#B25000",
        "tagline": "Autonomous stock reorder thresholds, near-expiry markdown prevention & counter warranty verification.",
    },
    {
        "name": "Manufacturing & Executive Data",
        "slug": "manufacturing-executive-data",
        "expected_count": 4,
        "icon": "factory",
        "accent": "#3A3A3C",
        "tagline": "Incoming CoA quality gates, batch BOM wastage variance, MRO breakdown repair guides & executive briefings.",
    },
    {
        "name": "Human Resources",
        "slug": "human-resources",
        "expected_count": 9,
        "icon": "users",
        "accent": "#AF52DE",
        "tagline": "Impartial CV screening, panel scheduling, onboarding/offboarding, payroll recon & workforce stress tests.",
    },
]


RAW_AGENTS: list[dict[str, Any]] = [
    # =========================================================================
    # 1. Banking & Financial Services (12)
    # =========================================================================
    {
        "slug": "bank-statement-analyzer",
        "sector": "Banking & Financial Services",
        "title": "Bank Statement Analyzer",
        "what_it_does": (
            "Reads high-volume multi-bank PDF and scanned statements, categorises inflows "
            "and outflows, identifies existing debt repayments, unusual transfers and returned "
            "cheques, and generates standard financial spreads and credit summaries."
        ),
        "value": (
            "Cuts underwriting turnaround by automating monthly cash-flow spreading "
            "and surfacing early warning signs."
        ),
        "live_url": "https://bank-statement-agent-259388273008.us-central1.run.app/",
        "default_path": "/studio/",
        "auth_mode": "starlette_session",
    },
    {
        "slug": "advisor-rm-insight-agent",
        "sector": "Banking & Financial Services",
        "title": "Advisor / Relationship Manager Insight Agent",
        "what_it_does": (
            "Aggregates client deposit, loan and wealth balances, account trends, payment "
            "patterns and market updates into pre-meeting briefings and tailored product "
            "recommendations for relationship managers."
        ),
        "value": (
            "Prepares relationship managers for client meetings in minutes, improving "
            "cross-sell, deposit retention and proactive service."
        ),
        "live_url": "https://banking-rm-pro-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "commercial-credit-cam-agent",
        "sector": "Banking & Financial Services",
        "title": "Commercial Credit Underwriting & Credit Approval Memo Agent",
        "what_it_does": (
            "Reviews a full commercial borrower file, calculates the debt service coverage, "
            "loan-to-value and debt-to-earnings ratios, runs interest-rate stress tests, "
            "and drafts a Credit Approval Memo with clickable page citations."
        ),
        "value": (
            "Compresses credit memo preparation from days to minutes while keeping "
            "Credit Committee standards consistent."
        ),
        "live_url": "https://banking-cam-generator-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "account-onboarding-prep-agent",
        "sector": "Banking & Financial Services",
        "title": "Account Onboarding File-Prep & Checklist Agent",
        "what_it_does": (
            "Reviews account-opening packets, checks completeness and expiry dates, flags "
            "cross-document spelling or address variations for officer review, extracts the "
            "shareholder table, and requests a public news digest from the Client Public "
            "News & Media Digest Agent."
        ),
        "value": (
            "Saves onboarding officers 45+ minutes per file; the officer keeps the final sign-off."
        ),
        "live_url": "https://banking-onboarding-prep-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "client-public-news-media-digest-agent",
        "sector": "Banking & Financial Services",
        "title": "Client Public News & Media Digest Agent",
        "what_it_does": (
            "Takes company and director names (from an officer or from the Account Onboarding "
            "agent), searches public business news, groups results including likely same-name "
            "coincidences, and exports a timestamped media clipping pack."
        ),
        "value": (
            "Removes 2+ hours of manual web searching per corporate client, with cited, neutral links."
        ),
        "live_url": "https://banking-media-digest-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "annual-overdraft-renewal-prep-agent",
        "sector": "Banking & Financial Services",
        "title": "Annual Overdraft Renewal Prep Agent",
        "what_it_does": (
            "Summarises 12 months of deposits, average overdraft utilisation and account "
            "conduct into a one-page annual renewal note."
        ),
        "value": (
            "Replaces the yearly manual Excel work behind overdraft rollover memos."
        ),
        "live_url": "https://banking-overdraft-renewal-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "loan-repayment-collections-agent",
        "sector": "Banking & Financial Services",
        "title": "Loan Repayment & Collections Follow-Up Agent",
        "what_it_does": (
            "Prioritises overdue loans by days past due and monthly instalment exposure, "
            "drafts empathetic email, SMS and call-script follow-ups, tracks promises-to-pay, "
            "and recommends restructuring or grace periods."
        ),
        "value": (
            "Improves early-stage recovery and reduces roll-rates into non-performing loans."
        ),
        "live_url": "https://banking-aida-collections-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "banking-policy-procedure-comparison-agent",
        "sector": "Banking & Financial Services",
        "title": "Banking Policy & Procedure Comparison Agent",
        "what_it_does": (
            "Compares updated policies or product circulars against existing branch standard "
            "operating procedures and lending handbooks, highlights clause additions and "
            "threshold changes side by side, and drafts a one-page redline summary."
        ),
        "value": (
            "Saves operations and governance teams hundreds of hours when updating manuals."
        ),
        "live_url": "https://banking-policy-comparison-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "multimodal-card-dispute-agent",
        "sector": "Banking & Financial Services",
        "title": "Multimodal Card Dispute & Chargeback Resolution Agent",
        "what_it_does": (
            "Guided mobile-chat and dispute workbench that reviews disputed transactions, "
            "receipt photos, ATM slips and customer voice notes together, matches claims to "
            "card-network chargeback rules, and issues provisional credit references."
        ),
        "value": (
            "Cuts card dispute handling time by combining conversational intake with image and voice review."
        ),
        "live_url": "https://banking-card-dispute-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "small-business-loan-review-agent",
        "sector": "Banking & Financial Services",
        "title": "Small Business Loan Review, Missing-Document Portal & Policy Rules Agent",
        "what_it_does": (
            "Extracts small business loan applications and statement cash flows, applies "
            "configurable lending rules with exact monthly instalment maths, offers a "
            "self-serve borrower upload portal for missing documents, and writes a five-part "
            "Credit Committee summary."
        ),
        "value": (
            "Combines accurate lending maths with clear summaries and faster collection of missing documents."
        ),
        "live_url": "https://loan-review-app-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "trade-finance-lc-discrepancy-checker",
        "sector": "Banking & Financial Services",
        "title": "Trade Finance & Letter of Credit Discrepancy Checker",
        "what_it_does": (
            "Cross-checks the letter of credit, bill of lading, invoice, insurance certificate "
            "and packing list against international documentary credit rules (UCP 600), spots "
            "port, weight, date or description mismatches, and drafts a discrepancy and waiver notice."
        ),
        "value": (
            "Turns a four-hour paper inspection into a structured check with exact rule references."
        ),
        "live_url": "https://banking-trade-lc-checker-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "executive-alco-balance-sheet-agent",
        "sector": "Banking & Financial Services",
        "title": 'Executive "Talk-to-Your-Balance-Sheet" & Asset-Liability Committee Stress-Test Agent',
        "what_it_does": (
            "Answers plain-English executive questions over the balance sheet, runs rate-shock "
            "and deposit run-off stress tests (net interest income, net interest margin, "
            "economic value of equity, liquidity coverage and net stable funding), inspects "
            "repricing ladders, and produces a one-page Asset-Liability Committee briefing note."
        ),
        "value": (
            "Gives senior executives and Treasury instant stress-test answers over governed numbers."
        ),
        "live_url": "https://banking-alco-treasury-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },

    # =========================================================================
    # 2. Public Sector (11)
    # =========================================================================
    {
        "slug": "enterprise-contracts-analyzer",
        "sector": "Public Sector",
        "title": "Enterprise Contracts Analyzer",
        "what_it_does": (
            "Reads uploaded contracts (PDF, Word and scanned agreements), extracts key terms, "
            "payment terms, auto-renewals and cancellation notice dates, flags high-risk "
            "clauses against company guidelines with suggested safer wording, compares drafts "
            "side by side, and answers plain-English questions with links to the exact page "
            "and paragraph."
        ),
        "value": (
            "Gives reviewers a fast, consistent first pass on every agreement, with page-level "
            "proof, before formal legal review."
        ),
        "live_url": "https://contracts-analyzer-z2hhdear5q-uc.a.run.app/",
        "auth_mode": "contracts_jwt",
    },
    {
        "slug": "public-candidate-screening-agent",
        "sector": "Public Sector",
        "title": "Candidate Screening & Credential Verification Agent",
        "what_it_does": (
            "Reads incoming resumes, cross-checks degrees and certifications against national "
            "clearinghouses and licensing boards through automated lookups, flags discrepancies, "
            "and gives an impartial suggestion on whether to progress, with the reasons "
            "recorded for recruiter review."
        ),
        "value": (
            "Replaces subjective screening with consistent, rule-based checks and impartial "
            "recommendations, keeping hiring fair and compliant. People make the final decision."
        ),
        "live_url": "https://candidates-screening-agent-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "it-service-desk-triage-agent",
        "sector": "Public Sector",
        "title": "IT Service Desk Triage Agent",
        "what_it_does": (
            "Integrates with ServiceNow or Jira Service Desk to run diagnostics on tickets, "
            "check permissions in the staff directory, auto-resolve standard requests "
            "(e.g. password resets), or route with diagnostic context to second-line support."
        ),
        "value": (
            "Clears routine service desk tickets quickly and equips technicians with "
            "contextual diagnostics up front."
        ),
        "live_url": "https://itsm-service-desk-259388273008.us-central1.run.app/dev-ui/?app=itsm_agent",
        "default_path": "/dev-ui/?app=itsm_agent",
        "secondary_url": "https://itsm-service-desk-259388273008.us-central1.run.app/queue",
        "secondary_label": "Open Ticket Queue",
        "auth_mode": "adk_direct",
    },
    {
        "slug": "public-supplier-invoice-sentinel",
        "sector": "Public Sector",
        "title": "Supplier Invoice Sentinel",
        "what_it_does": (
            "Reads supplier invoices (PDF or image), extracts line items, performs a three-way "
            "match against the purchase order and goods receipt from the company’s business "
            "system, checks for duplicates, applies price and quantity tolerances, queues "
            "clean matches for approval, and raises exceptions with a plain-language reason."
        ),
        "value": (
            "Automates accounts-payable matching so staff only intervene on exceptions, "
            "and stops duplicate or overpriced invoices before they are paid."
        ),
        "live_url": "https://supplier-invoice-sentinel-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "expensesentry-agent",
        "sector": "Public Sector",
        "title": "ExpenseSentry",
        "what_it_does": (
            "Scans receipts, categorises expense line items, evaluates them against "
            "organisational policy caps, auto-approves compliant low-threshold claims, "
            "and flags anomalies."
        ),
        "value": (
            "Consistently enforces expense policy while relieving managers from routine manual audits."
        ),
        "live_url": "https://expense-auditor-259388273008.us-central1.run.app/",
        "auth_mode": "expense_jwt",
    },
    {
        "slug": "edms-document-cataloguing-agent",
        "sector": "Public Sector",
        "title": "Document Management Cleanup & Cataloguing Agent",
        "what_it_does": (
            "Processes unprocessed document folders, retrieves files, stores them in "
            "controlled locations, and records metadata in a tracked register."
        ),
        "value": (
            "Clears document backlogs automatically while leaving a clean audit trail."
        ),
        "live_url": "https://edms-catalogue-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "supplier-prequalification-agent",
        "sector": "Public Sector",
        "title": "Supplier Prequalification Agent",
        "what_it_does": (
            "Checks each supplier's registration, licences, tax and insurance certificates, "
            "financial statements and past performance against the prequalification checklist, "
            "flags expired or missing documents, checks sanctions and debarment lists, and "
            "produces a checklist report for the procurement officer."
        ),
        "value": (
            "Speeds up paperwork for every applicant so officers focus on exceptions. "
            "The officer still makes the prequalification decision."
        ),
        "live_url": "https://supplier-prequalification-agent-259388273008.us-central1.run.app",
        "auth_mode": "prequal_jwt",
    },
    {
        "slug": "password-protected-government-chatbot",
        "sector": "Public Sector",
        "title": "Password-Protected Government Chatbot",
        "what_it_does": (
            "Provides a government-wide assistant for citizen enquiries, requiring initial "
            "authentication (one-time password or portal login) to control user query permissions."
        ),
        "value": (
            "Delivers 24/7 authenticated citizen support with controlled system usage."
        ),
        "live_url": "https://kenya-public-info-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "nil-tax-return-submission-agent",
        "sector": "Public Sector",
        "title": "Nil Tax Return Submission Agent",
        "what_it_does": (
            "Guides taxpayers with zero income or taxable activity through eligibility "
            "pre-checks, form completion and filing confirmation."
        ),
        "value": (
            "Simplifies tax compliance for citizens and reduces follow-up overhead for tax authorities."
        ),
        "live_url": "https://nilfile-assistant-259388273008.us-central1.run.app/",
        "channel_badge": "Available on WhatsApp + Web Simulator",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "pre-filled-licence-renewal-agent",
        "sector": "Public Sector",
        "title": "Pre-Filled Licence Renewal Agent",
        "what_it_does": (
            "Triggers 30 days before licence expiry, fetches historical data, generates "
            "renewal applications, prompts holders via message, and processes payment "
            "upon confirmation."
        ),
        "value": (
            "Reduces permit processing from full forms to simple confirmations, preventing "
            "lapses in renewals."
        ),
        "live_url": "https://expiryguard-259388273008.us-central1.run.app/login",
        "default_path": "/",
        "auth_mode": "expiryguard_nextauth",
    },
    {
        "slug": "agricultural-pest-disease-diagnosis-agent",
        "sector": "Public Sector",
        "title": "Agricultural Pest & Disease Diagnosis Agent",
        "what_it_does": (
            "Analyses crop photos using multimodal vision models, compares images with a "
            "database of pests and diseases, and provides a preliminary diagnosis and "
            "treatment steps for human extension officer review."
        ),
        "value": (
            "Accelerates agricultural diagnosis for farmers while preserving expert oversight."
        ),
        "live_url": "https://crop-pest-and-disease-advisor-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },

    # =========================================================================
    # 3. Insurance (12)
    # =========================================================================
    {
        "slug": "motor-policy-renewal-intelligence-agent",
        "sector": "Insurance",
        "title": "Motor Policy Renewal Intelligence Agent",
        "what_it_does": (
            "Identifies expiring motor policies 30, 14 and 7 days ahead, calculates renewal "
            "sum insured, depreciation and no-claims discount with deterministic rating rules, "
            "sends renewal invites, tracks required valuations, and offers a self-serve "
            "renewal portal."
        ),
        "value": (
            "Lifts motor retention and removes manual renewal quoting across thousands of "
            "monthly expiries."
        ),
        "live_url": "https://sybyl.site/ria",
        "auth_mode": "external_direct",
    },
    {
        "slug": "premium-receivables-collections-agent",
        "sector": "Insurance",
        "title": "Premium Receivables & Collections Follow-Up Agent",
        "what_it_does": (
            "Prioritises overdue premiums across ageing buckets, drafts tailored email, "
            "SMS and call-script reminders, logs promises-to-pay, enforces communication "
            "guardrails, and reconciles incoming remittances."
        ),
        "value": (
            "Accelerates premium collection and reduces cancellations and bad-debt write-offs."
        ),
        "live_url": "https://aar-aida-web-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "insurance-rm-portfolio-insight-agent",
        "sector": "Insurance",
        "title": "Relationship Manager & Portfolio Insight Agent",
        "what_it_does": (
            "Unifies a client’s policies, claims history, renewal calendar, document expiry "
            "dates and public news into one workbench with pre-meeting briefings and "
            "coverage-gap recommendations."
        ),
        "value": (
            "Relationship managers and brokers walk into every renewal fully prepared in 60 seconds."
        ),
        "live_url": "https://insurance-rm-engine-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "multimodal-motor-claims-intake-agent",
        "sector": "Insurance",
        "title": "Multimodal Motor Claims Intake & Vetting Agent",
        "what_it_does": (
            "Guided first-notice-of-loss intake and vetting that reviews the claimant "
            "declaration, police abstract, damage photos and garage estimate side by side, "
            "compares declared and observed impact zones, and produces a claim assessment "
            "and repair approval sheet."
        ),
        "value": (
            "Cuts motor claim vetting from days to minutes and surfaces discrepancies for the adjuster."
        ),
        "live_url": "https://insurance-claims-agent-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "medical-preauth-bill-scrubbing-agent",
        "sector": "Insurance",
        "title": "Medical Pre-Authorization & Discharge Bill Scrubbing Agent",
        "what_it_does": (
            "Checks itemised hospital bills and pre-auth requests against the benefit "
            "schedule, separates payable items from non-payable consumables and sub-limit "
            "excesses with clause citations, and prints a settlement voucher."
        ),
        "value": (
            "Replaces manual line-by-line bill scrubbing and shortens hospital discharge waits."
        ),
        "live_url": "https://insurance-medical-bill-scrubber-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "broker-multi-insurer-quote-comparison",
        "sector": "Insurance",
        "title": "Broker Multi-Insurer Quote Slip & Coverage Comparison",
        "what_it_does": (
            "Normalises competing underwriter quote slips into a side-by-side matrix of "
            "premium, rate, deductibles, extensions, warranties and subjectivities, and "
            "prints a client placement note."
        ),
        "value": (
            "Saves brokers 2+ hours of Excel work per placement and exposes hidden deductible traps."
        ),
        "live_url": "https://insurance-broker-quote-comparison-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "policy-wording-endorsement-redline-agent",
        "sector": "Insurance",
        "title": "Policy Wording & Endorsement Redline Comparison Agent",
        "what_it_does": (
            "Compares expiring and renewal wordings or reinsurance endorsements, highlights "
            "changed sub-limits, deductibles, new exclusions and stricter warranties, and "
            "exports a one-page redline summary."
        ),
        "value": (
            "Removes hours of page-by-page reading for underwriters, brokers and risk managers."
        ),
        "live_url": "https://insurance-policy-wording-diff-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "commercial-property-risk-survey-agent",
        "sector": "Insurance",
        "title": "Commercial Property Risk Survey & Underwriting Slip Prep",
        "what_it_does": (
            "Reads surveyor reports, site photos and asset schedules, extracts construction, "
            "occupancy, protection and exposure facts and estimated maximum loss, tracks "
            "30/60/90-day improvement subjectivities, and drafts a one-page underwriting risk slip."
        ),
        "value": (
            "Compresses property underwriting prep from hours to minutes and keeps safety "
            "subjectivities tracked."
        ),
        "live_url": "https://insurance-property-risk-survey-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "group-life-medical-census-agent",
        "sector": "Insurance",
        "title": "Group Life & Medical Census Validation & Endorsement Agent",
        "what_it_does": (
            "Validates employee and dependant census rosters, checks missing data and age "
            "bands, flags executives above the free cover limit for medical underwriting, "
            "computes pro-rata premiums, and prints an endorsement schedule."
        ),
        "value": (
            "Replaces weekly spreadsheet work with accurate pro-rata endorsement maths."
        ),
        "live_url": "https://insurance-group-census-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "reinsurance-treaty-facultative-slip-agent",
        "sector": "Insurance",
        "title": "Reinsurance Treaty Capacity & Facultative Placement Slip Agent",
        "what_it_does": (
            "Tests large risks against the treaty capacity table, calculates net retention, "
            "automatic treaty share and the facultative excess needing placement, and "
            "generates a facultative placement slip."
        ),
        "value": (
            "Removes treaty allocation errors and prepares market-ready facultative placement "
            "slips in seconds."
        ),
        "live_url": "https://insurance-reinsurance-fac-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "motor-valuation-inspection-checklist-agent",
        "sector": "Insurance",
        "title": "Motor Valuation & Pre-Insurance Inspection Checklist Agent",
        "what_it_does": (
            "Cross-checks logbook, valuer report and inspection photos against the policy "
            "schedule within the 14-day post-renewal window, verifies chassis number, plate, "
            "owner and sum insured, and flags pre-existing damage."
        ),
        "value": (
            "Automates post-renewal valuation checks alongside the Motor Policy Renewal "
            "Intelligence Agent and prevents under- or over-insurance disputes."
        ),
        "live_url": "https://insurance-motor-valuation-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "executive-loss-ratio-reserve-stress-agent",
        "sector": "Insurance",
        "title": 'Executive "Talk-to-Your-Loss-Ratio" & Claims Reserve Stress-Test Agent',
        "what_it_does": (
            "Answers executive questions over gross written premium, net earned premium, "
            "and loss, expense and combined ratios by class, with sliders for claims "
            "inflation, frequency spikes and catastrophe events, and a one-page actuarial "
            "and board briefing note."
        ),
        "value": (
            "Gives chief executives, finance directors and actuaries instant reserve "
            "stress-test answers over governed numbers."
        ),
        "live_url": "https://insurance-loss-ratio-alco-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },

    # =========================================================================
    # 4. Sales & Distribution (6)
    # =========================================================================
    {
        "slug": "po-to-sales-order-resolution-agent",
        "sector": "Sales & Distribution",
        "title": "Purchase-Order-to-Sales-Order Resolution Agent",
        "what_it_does": (
            "Ingests customer purchase orders (PDF or email), resolves fuzzy customer and "
            "product names against the product catalogue, converts multi-currency prices, "
            "runs six deterministic checks, and auto-posts clean orders or routes exceptions "
            "to a human reviewer."
        ),
        "value": (
            "Cuts order entry from 18 minutes to under 15 seconds and catches unapproved "
            "price deductions before dispatch."
        ),
        "live_url": "https://lpo-agent-service-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "delivery-watching-short-delivery-credit-note-agent",
        "sector": "Sales & Distribution",
        "title": "Delivery Watching & Short-Delivery Credit-Note Agent",
        "what_it_does": (
            "Compares the delivery record in the business system with the signed proof of "
            "delivery, flags late or short-shipped lines, calculates the credit-note value "
            "in Python, and drafts a credit note and a proactive customer email."
        ),
        "value": (
            "Resolves short-delivery credit notes in under 60 seconds instead of a 14-day dispute cycle."
        ),
        "live_url": "https://distribution-pod-dispute-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "key-account-manager-health-agent",
        "sector": "Sales & Distribution",
        "title": "Key Account Manager Health & Deal-Stall Agent",
        "what_it_does": (
            "Monitors top accounts for order drop-offs, shrinking baskets, stalled quotes, "
            "fill-rate slips and overdue receivables, and generates a 60-second account "
            "health brief with a suggested replenishment draft."
        ),
        "value": (
            "Surfaces at-risk accounts the moment ordering dips, lifting retention."
        ),
        "live_url": "https://distribution-key-account-rm-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "competitive-price-tracker-agent",
        "sector": "Sales & Distribution",
        "title": "Competitive Price Tracker & Flash-Discount Strategy Agent",
        "what_it_does": (
            "Visually reads competitor websites, logs product prices over time, and uses "
            "Gemini to separate short-term flash promos from structural cuts and recommend "
            "margin-safe responses."
        ),
        "value": (
            "Gives commercial teams an early warning on competitor pricing without manual price checks."
        ),
        "live_url": "https://distribution-competitive-price-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "sales-outreach-agent",
        "sector": "Sales & Distribution",
        "title": "Sales Outreach Agent",
        "what_it_does": (
            "Runs campaign-driven outbound email for business sales teams. Researches each "
            "prospect with live Google Search citations, grounds every product claim in "
            "approved company collateral, drafts a personalised opening and follow-ups, "
            "and keeps an audit trail with unsubscribe handling for data protection "
            "compliance. A person approves every email before it is sent."
        ),
        "value": (
            "Replaces hours of manual prospect research per campaign with verifiable, "
            "personalised outreach that protects brand and sending reputation."
        ),
        "live_url": "https://sales-outreach-agent-259388273008.us-central1.run.app",
        "auth_mode": "sales_outreach_session",
    },
    {
        "slug": "sales-visit-planning-assistant",
        "sector": "Sales & Distribution",
        "title": "Sales Visit Planning Assistant",
        "what_it_does": (
            "A conversational assistant for field salespeople that researches target "
            "companies, finds free slots and books visits in the calendar, keeps accounts, "
            "opportunities and visit logs current in the customer relationship system, and "
            "remembers the salesperson across sessions."
        ),
        "value": (
            "Cuts the admin around client visits so salespeople spend more of the week with customers."
        ),
        "live_url": "https://sales-assistant-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },

    # =========================================================================
    # 5. Finance Reconciliation (4)
    # =========================================================================
    {
        "slug": "finance-supplier-invoice-sentinel-three-way",
        "sector": "Finance Reconciliation",
        "title": "Supplier Invoice Sentinel: Three-Way Invoice Match",
        "what_it_does": (
            "Extracts supplier invoices, matches them line by line to purchase orders and "
            "goods receipts, verifies tax and arithmetic in Python, blocks duplicates, "
            "posts clean invoices as draft entries in the accounting system, and routes "
            "variances to an exceptions queue."
        ),
        "value": (
            "Automates 80%+ of routine accounts payable matching and prevents duplicate or "
            "overbilled payments."
        ),
        "live_url": "https://supplier-invoice-sentinel-259388273008.us-central1.run.app/dev-ui/?app=supplier_invoice_sentinel",
        "default_path": "/dev-ui/?app=supplier_invoice_sentinel",
        "auth_mode": "adk_direct",
    },
    {
        "slug": "customer-payment-cash-allocation-agent",
        "sector": "Finance Reconciliation",
        "title": "Customer Payment & Cash Allocation Reconciliation Agent",
        "what_it_does": (
            "Reconciles unallocated bank and mobile money deposits against open invoices "
            "using specified-invoice matching or an oldest-first waterfall, and generates "
            "the cash allocation journal for the accounting system."
        ),
        "value": (
            "Clears the unallocated cash backlog that falsely blocks customer credit limits."
        ),
        "live_url": "https://finance-cash-app-recon-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "retail-pos-settlement-reconciliation-agent",
        "sector": "Finance Reconciliation",
        "title": "Retail Till, Mobile Money, Card & Bank Settlement Reconciliation Agent",
        "what_it_does": (
            "Runs a daily four-way tender reconciliation across till end-of-day reports, "
            "mobile money statements, card acquirer files and bank credits, isolating "
            "commission overcharges, timing cutoffs, till shortages and duplicate reversals."
        ),
        "value": (
            "Turns a six-hour daily spreadsheet task into a 45-second reconciliation for "
            "multi-branch retailers."
        ),
        "live_url": "https://retail-pos-settlement-recon-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "supplier-statement-reconciliation-agent",
        "sector": "Finance Reconciliation",
        "title": "Supplier Statement Reconciliation & Aged Creditor Matching Agent",
        "what_it_does": (
            "Reconciles a supplier statement of account against the vendor ledger in the "
            "business system, classifies each difference (missing invoices, payments in "
            "transit, unrecorded debit notes, currency differences), and drafts the "
            "supplier query email."
        ),
        "value": (
            "Cuts month-end vendor statement reconciliation time by 90%."
        ),
        "live_url": "https://finance-vendor-statement-recon-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },

    # =========================================================================
    # 6. Retail Operations (3)
    # =========================================================================
    {
        "slug": "live-inventory-threshold-reorder-agent",
        "sector": "Retail Operations",
        "title": "Live Inventory Threshold & Autonomous Reorder Agent",
        "what_it_does": (
            "Watches branch and warehouse stock against reorder thresholds calculated from "
            "business intelligence reports, drafts a purchase requisition when stock falls "
            "below the safe level, and escalates unusual demand spikes to a buyer."
        ),
        "value": (
            "Cuts stockouts and dead stock together by reacting to real demand continuously."
        ),
        "live_url": "https://retail-reorder-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "near-expiry-markdown-shrinkage-agent",
        "sector": "Retail Operations",
        "title": "Near-Expiry Markdown & Shrinkage Prevention Agent",
        "what_it_does": (
            "Compares remaining shelf life with sales velocity at batch level, identifies "
            "stock that will expire before selling through, and recommends progressive "
            "markdowns, inter-branch transfers or bundling."
        ),
        "value": (
            "Reduces fresh, dairy and pharmacy expiry write-offs by an estimated 25 to 40%."
        ),
        "live_url": "https://retail-markdown-expiry-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "customer-return-warranty-verification-agent",
        "sector": "Retail Operations",
        "title": "Customer Return & Warranty Verification Agent",
        "what_it_does": (
            "Verifies counter returns in three steps: receipt and serial check, return "
            "window and warranty check, then an approve, repair or reject decision slip."
        ),
        "value": (
            "Protects store cash from invalid returns while honouring genuine warranty claims."
        ),
        "live_url": "https://retail-returns-warranty-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },

    # =========================================================================
    # 7. Manufacturing & Executive Data (4)
    # =========================================================================
    {
        "slug": "raw-material-coa-quality-gate-agent",
        "sector": "Manufacturing & Executive Data",
        "title": "Raw Material Certificate of Analysis & Incoming Quality Control Gate Agent",
        "what_it_does": (
            "Reads supplier laboratory certificate of analysis PDFs at the factory gate, "
            "validates every parameter against the material specification in deterministic "
            "Python, blocks out-of-spec lots, and issues a release or quarantine certificate."
        ),
        "value": (
            "Catches off-spec raw materials in 20 seconds, preventing batch contamination and recalls."
        ),
        "live_url": "https://manufacturing-quality-coa-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "production-batch-cost-wastage-agent",
        "sector": "Manufacturing & Executive Data",
        "title": "Production Batch Cost & Material Wastage Reconciliation Agent",
        "what_it_does": (
            "Compares finished batches against the standard recipe and planned shift hours, "
            "and breaks cost overruns into material wastage, raw material price difference "
            "and machine downtime cost."
        ),
        "value": (
            "Explains why a batch exceeded budget the same day, not 20 days after month-end."
        ),
        "live_url": "https://manufacturing-bom-yield-variance-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "factory-machine-breakdown-repair-agent",
        "sector": "Manufacturing & Executive Data",
        "title": "Factory Machine Breakdown & Repair Guide Agent",
        "what_it_does": (
            "Reads the breakdown report, pulls step-by-step repair instructions with page "
            "numbers from the maintenance manual, checks spare-part stock, and issues a "
            "technician job card."
        ),
        "value": (
            "Gets stopped lines running faster with instant repair guidance and part availability."
        ),
        "live_url": "https://manufacturing-maintenance-mro-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "executive-ceo-finance-auditor-data-agents",
        "sector": "Manufacturing & Executive Data",
        "title": "Chief Executive, Finance Manager & Auditor Executive Data Agents",
        "what_it_does": (
            "Over the business intelligence layer: weekly chief executive briefings across "
            "agents, real-time budget and liquidity variance alerts, and scheduled forensic "
            "scans of weekend and above-threshold postings."
        ),
        "value": (
            "One always-current command centre instead of five dashboards to reconcile manually."
        ),
        "live_url": "https://executive-sop-margin-stress-agent-259388273008.us-central1.run.app",
        "auth_mode": "spa_storage",
    },

    # =========================================================================
    # 8. Human Resources (9)
    # =========================================================================
    {
        "slug": "hr-candidates-screening-agent",
        "sector": "Human Resources",
        "title": "Candidates Screening Agent",
        "what_it_does": (
            "Builds an evaluation rubric from a job description, reads bulk CVs, checks "
            "mandatory criteria, and gives each applicant an impartial assessment with "
            "plain-English strengths and gaps, exported as a ranked Excel shortlist for "
            "the recruiter."
        ),
        "value": (
            "Gives every applicant a fair, impartial review against the same criteria, so "
            "recruiters can focus on the quality of the shortlist and the final decision."
        ),
        "live_url": "https://candidates-screening-agent-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "interview-scheduler-agent",
        "sector": "Human Resources",
        "title": "Interview Scheduler Agent",
        "what_it_does": (
            "Coordinates multi-stage interview panels by checking Google Calendar "
            "availability, emailing slot options to candidates, and booking Google Meet links."
        ),
        "value": (
            "Eliminates 5 to 10 scheduling emails per candidate and prevents double-booked panels."
        ),
        "live_url": "https://interview-scheduler-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "hr-onboarding-pro-agent",
        "sector": "Human Resources",
        "title": "HR Onboarding Pro Agent",
        "what_it_does": (
            "Generates offer letter PDFs, captures online e-signatures, then coordinates "
            "four setup agents: IT email, laptop, commute pass and health insurance."
        ),
        "value": (
            "Prevents pre-Day-One drop-off and has every new hire ready on Day 1."
        ),
        "live_url": "https://hr-onboarding-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "hr-offboarding-pro-agent",
        "sector": "Human Resources",
        "title": "HR Offboarding Pro Agent",
        "what_it_does": (
            "Runs the reverse of onboarding: insurance cancellation, pass revocation, "
            "laptop return and IT deactivation, then calculates final dues, captures "
            "clearance sign-off, and issues a Certificate of Service."
        ),
        "value": (
            "Closes security gaps from active accounts after exit and produces instant exit documentation."
        ),
        "live_url": "https://hr-offboarding-pro-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "payroll-variance-statutory-recon-agent",
        "sector": "Human Resources",
        "title": "Payroll Variance, Statutory Compliance & Payslip Recon Agent",
        "what_it_does": (
            "Compares draft payroll with last month and HR master records, flags headcount "
            "changes, pay jumps, bank-account swaps and ghost-worker risk, and verifies "
            "statutory deductions (income tax, social security, health insurance and housing levy)."
        ),
        "value": (
            "Catches payroll errors and unauthorised bank changes before salaries are paid."
        ),
        "live_url": "https://hr-payroll-recon-agent-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "attendance-clock-in-leave-agent",
        "sector": "Human Resources",
        "title": "Attendance Clock-In/Out & Leave Notification Agent",
        "what_it_does": (
            "Checks clock-in and clock-out times against approved leave, calculates hours "
            "worked versus shift hours, and notifies HR of missed hours or absences with "
            "no leave application."
        ),
        "value": (
            "Gives HR an instant daily exception list without manual cross-checking."
        ),
        "live_url": "https://hr-attendance-leave-agent-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "employee-hr-helpdesk-agent",
        "sector": "Human Resources",
        "title": "Employee HR Helpdesk Agent",
        "what_it_does": (
            "Answers everyday staff questions (leave, medical cover, payroll dates, claims, "
            "office guidelines) from the official handbook and creates an HR ticket when "
            "human follow-up is needed."
        ),
        "value": (
            "Resolves 70%+ of routine HR questions immediately."
        ),
        "live_url": "https://hr-helpdesk-agent-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "learning-certification-expiry-skills-agent",
        "sector": "Human Resources",
        "title": "Learning, Certification Expiry & Skills Matrix Agent",
        "what_it_does": (
            "Tracks licences, safety certifications, training hours and training bonds, "
            "and alerts HR and managers 30, 60 and 90 days before expiry."
        ),
        "value": (
            "Prevents compliance breaches from expired staff licences."
        ),
        "live_url": "https://hr-skills-compliance-agent-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
    {
        "slug": "executive-workforce-attrition-stress-agent",
        "sector": "Human Resources",
        "title": 'Executive "Talk-to-Your-Workforce" & Attrition Stress-Test Agent',
        "what_it_does": (
            "Workforce analytics for the chief human resources officer and chief executive "
            "covering headcount, turnover and hiring speed, with sliders to test the budget "
            "impact of salary reviews or attrition changes."
        ),
        "value": (
            "Replaces static monthly HR spreadsheets with live wage-bill scenario planning."
        ),
        "live_url": "https://hr-workforce-analytics-agent-259388273008.us-central1.run.app/",
        "auth_mode": "spa_storage",
    },
]


def _build_catalog() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    sector_meta = {s["name"]: s for s in SECTORS_ORDER}
    enriched: list[dict[str, Any]] = []
    by_slug: dict[str, dict[str, Any]] = {}

    for idx, item in enumerate(RAW_AGENTS, start=1):
        sec_info = sector_meta[item["sector"]]
        record = {
            "id": f"{idx:02d}",
            "index": idx,
            "slug": item["slug"],
            "sector": item["sector"],
            "sector_slug": sec_info["slug"],
            "sector_accent": sec_info["accent"],
            "title": item["title"],
            "what_it_does": item["what_it_does"],
            "value": item["value"],
            "live_url": item["live_url"],
            "default_path": item.get("default_path", "/"),
            "secondary_url": item.get("secondary_url"),
            "secondary_label": item.get("secondary_label"),
            "channel_badge": item.get("channel_badge"),
            "auth_mode": item.get("auth_mode", "spa_storage"),
        }
        enriched.append(record)
        by_slug[record["slug"]] = record

    return enriched, by_slug


AGENTS_CATALOG, AGENTS_BY_SLUG = _build_catalog()


def get_catalog_summary() -> dict[str, Any]:
    """Return sector breakdown and total agent count."""
    sectors_out: list[dict[str, Any]] = []
    for sec in SECTORS_ORDER:
        sec_agents = [a for a in AGENTS_CATALOG if a["sector"] == sec["name"]]
        sectors_out.append(
            {
                **sec,
                "count": len(sec_agents),
                "agents": sec_agents,
            }
        )
    return {
        "total_agents": len(AGENTS_CATALOG),
        "total_sectors": len(SECTORS_ORDER),
        "design_principles": DESIGN_PRINCIPLES,
        "sectors": sectors_out,
    }
