# ReadyCheck ⚖️ — Autonomous Grievance Audit & Policy Watchdog

[![AZINHACK 26](https://img.shields.io/badge/AZINHACK%20%E2%80%9926-USAR%20GGSIPU-10B981?style=for-the-badge)](https://github.com)
[![TinyFish Powered](https://img.shields.io/badge/TinyFish-Live%20Web%20Agents-06B6D4?style=for-the-badge)](https://tinyfish.ai)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20REST-009688?style=for-the-badge)](https://fastapi.tiangolo.com)
[![Tests Passing](https://img.shields.io/badge/Unit%20Tests-8%2F8%20Passing-success?style=for-the-badge)](backend/tests)

> **Evidence-First E-Commerce Compliance & Dark-Pattern Watchdog for India's 500M+ Online Shoppers.**  
> Built for **AZINHACK ’26** at the University School of Automation & Robotics (USAR), GGSIPU East Delhi Campus.
> 
CHECK IT OUT  https://azinhack.onrender.com/

---

## 🎯 The Problem

1. **The E-Commerce Grievance Blackhole:** In 2025, over **5.11 Lakh e-commerce complaints** were received by India's National Consumer Helpline (NCH). Consumers waste hours fighting automated FAQ chatbot loops without reaching the legally mandated Grievance Officer.
2. **The New Regulatory Mandate:** Under India's **Amended Consumer Protection (E-Commerce) Rules (effective Jan 1, 2027)**, platforms are legally required to publish designated Grievance Officers, nodal contact emails, telephone numbers, and 48-hour acknowledgement timelines.
3. **Silent Overnight Terms Shifting:** Platforms quietly alter return windows (e.g. 14 days $\to$ 48 hours) or warranty fine-print without public changelogs, leaving consumers with zero historical evidence in consumer court.

---

## 🚀 Key Features

* **Autonomous Discovery:** TinyFish Search API scopes the target company's official domain to locate buried grievance and dispute redressal pages.
* **Anti-Bot Markdown Extraction:** TinyFish Fetch API extracts clean text without Cloudflare or anti-crawler obstacles, using ETag/Last-Modified caching to prevent stale fetches.
* **100% Anti-Hallucination Grounding:** Stringent grounding engine rejects unverified claims. Every verified contact field must verbatim exist inside an official source quote.
* **Silent Policy Change Watchdog:** Cryptographic SHA-256 snapshots track policies over time, running sequence-matching diffs and classifying shifts (`contact_details`, `response_timeline`, `complaint_process`).
* **1-Click Regulatory Evidence Dossier:** Generates tamper-evident, court-admissible audit reports with cryptographic hashes and pre-formatted escalation notices for NCH / CCPA.
* **Live Agent Activity Stream:** Real-time visual terminal telemetry in the browser demonstrating agent execution steps, search queries, and ML classification confidence.

---

## 🛠️ Deep TinyFish Integration

ReadyCheck integrates all core tiers of the **TinyFish SDK**:

| TinyFish Capability | Project Implementation |
|---|---|
| **Search API** | Queries live official domain endpoints: `{company} grievance officer escalation policy` with strict domain bounding. |
| **Fetch API** | Retrieves anti-bot sanitized Markdown with ETag headers, cutting redundant crawling costs. |
| **Web Agent (Fallback)** | Bounded headless agent streams through dynamic JavaScript/SPA pages (React/Next.js) to parse complex tables into strict Pydantic JSON schemas. |
| **Browser Infrastructure** | Headless Playwright & CDP instances handle DOM hydration and dynamic redirects. |

---

## 💻 Quickstart (Windows PowerShell)

The existing virtual environment is located in `tinyfish/`:

```powershell
# 1. Activate Virtual Environment
.\tinyfish\Scripts\Activate.ps1

# 2. Install Dependencies (if not already installed)
python -m pip install -r requirements.txt

# 3. Start the FastAPI Server
python -m uvicorn backend.app.main:app --reload
```

Open **`http://127.0.0.1:8000`** in your browser.

* **Demo Mode (`DEMO_MODE=true` in `.env`):** Features pre-seeded instant audits for **Meesho**, **boAt Lifestyle**, **Nykaa**, and **Sample Store**, plus full Policy Watch change detection without requiring active API quotas.
* **Live Mode (`DEMO_MODE=false` in `.env`):** Enter your `TINYFISH_API_KEY` in `.env` to execute live autonomous crawls on the web.

---

## 🧪 Automated Verification & Tests

To execute the unit test suite verifying domain safety, SSRF rejection, quote grounding, ML classification, and policy diffs:

```powershell
.\tinyfish\Scripts\python.exe -m unittest discover -s backend/tests -v
```

**Result: 8/8 Tests Passing (100% green).**

---

## 👥 Kitten Team (USAR, GGSIPU)

* **Khushi Maheshwari** — B.Tech Robotics & Automation, USAR, GGSIPU East Delhi Campus.
* **Pitch Deck:** [`docs/ReadyCheck_Winner_Pitch_Deck.pptx`](docs/ReadyCheck_Winner_Pitch_Deck.pptx) & `Downloads/ReadyCheck_Winner_Pitch_Deck.pptx`.

