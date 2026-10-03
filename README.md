# KwizeraGate

**Author:** Cynthia Moraa (`cynthiamogaka49`)
**Company / Solution:** Modus Chora Studio · KwizeraGate
**Pathway:** Cybersecurity — IBM Guardium · IBM QRadar · IBM Verify
**Target Region:** Burundi (BurundiPay Digital Public Infrastructure)
**Cornerstone Project — IBM x MC Studio Program 2026**

---

## 🌐 Live Environment Links

| What                 | URL                                                                                                                        |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Video Demo**       | [KwizeraGate VideoDemo.mp4](https://1drv.ms/v/c/2bb2f9afc8ae1149/IQA7cfk1EQ4KT6hMsgMybZw7AYCfWnav5GF6lGaW5Ze5EzM?e=b4ilEA) |
| **Live Dashboard**   | https://kwizeragate-app-kwizeragate.apps.itz-7zzjya.hub04-lb.techzone.ibm.com/                                             |
| **Swagger API Docs** | https://kwizeragate-app-kwizeragate.apps.itz-7zzjya.hub04-lb.techzone.ibm.com/docs                                         |
| **Health Probe**     | https://kwizeragate-app-kwizeragate.apps.itz-7zzjya.hub04-lb.techzone.ibm.com/health                                       |

> **Cluster:** TechZone OCPv · OpenShift on IBM Cloud · `itz-7zzjya` · Deployed October 2, 2026

---

## What Is KwizeraGate?

KwizeraGate is a cloud-native, **Zero-Trust payment entry middleware** designed to secure
mobile-wallet transactions across Burundi's Digital Public Infrastructure (DPI).

It replaces vulnerable SMS-OTP authentication flows with **adaptive risk-based Multi-Factor
Authentication** powered by IBM Verify, and streams every transaction through a real-time
behavioral anomaly pipeline backed by IBM QRadar — before any payment reaches the core switch.

---

## IBM Security Stack

| IBM Technology   | Integration Role                                                                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **IBM Verify**   | Adaptive MFA — evaluates IP address and device fingerprint; triggers biometric push or step-up authentication for unrecognized origins outside Bujumbura                 |
| **IBM QRadar**   | SIEM log ingestion — FastAPI streams structured JSON transaction events to QRadar; custom rules detect anomalies and fire a webhook to auto-suspend the merchant session |
| **IBM Guardium** | SQL ledger protection — monitors database traffic on the PostgreSQL instance; blocks unauthorized `SELECT *`, bulk reads, and DDL (`DROP`/`TRUNCATE`) operations         |

---

## Tech Stack

| Layer             | Technology                                      |
| ----------------- | ----------------------------------------------- |
| Backend Framework | Python 3.11 · FastAPI · Uvicorn                 |
| Database (dev)    | SQLite (zero-setup, file-based)                 |
| Database (prod)   | PostgreSQL 15 (Docker Compose)                  |
| ORM               | SQLAlchemy 2.x                                  |
| Auth              | JWT (`python-jose`) · Adaptive MFA (IBM Verify) |
| Containerization  | Docker · Docker Compose                         |
| Deployment Target | OpenShift on IBM Cloud (TechZone OCPv — ROKS)   |
| SIEM              | IBM QRadar (log stream + webhook)               |
| Data Security     | IBM Guardium (external DB observer)             |

---

## Quick Start (Local — no Docker required)

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment variables
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux

# 4. Seed the database (REQUIRED before first run — creates tables + test merchant)
python db_init.py

# 5. Start the API server
uvicorn main:app --reload --port 8000
```

- Dashboard: **http://localhost:8000/**
- API docs: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**

---

## Quick Start (Docker — full Postgres stack)

```bash
# Edit .env — change DATABASE_URL to the Postgres line (see .env.example comments)
docker compose up --build
```

The app will be available at **http://localhost:8000**. Postgres data is persisted in a named volume.

---

## Running the Security Test Suite

**Important:** Run these in order — the server must be running first.

```bash
# Terminal 1 — start the server
uvicorn main:app --reload --port 8000

# Terminal 2 — seed the DB (resets test merchant to active between runs)
python db_init.py

# Terminal 2 — run all 5 security scenarios
python test_attacks.py
```

Expected output — five security scenarios with PASS/FAIL:

```
[1] Valid auth (Bujumbura IP)              PASS
[2] Spoofed IP -> IBM Verify step-up       PASS
[3] Unknown merchant API key               PASS
[4] Valid BIF transfer + QRadar log        PASS
[5] Suspended merchant blocked             PASS

Results: 5/5 passed
```

---

## 🚀 Live Deployment — TechZone OpenShift Cluster

> **Deployed:** Phase 3 Practical — IBM CLP111 Cybersecurity Pathway
> **Cluster:** TechZone OCPv · OpenShift on IBM Cloud · `itz-7zzjya`
> **Submitted:** October 2, 2026

| Item                 | Result                                                                                                                        |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Video Demo**       | [KwizeraGate VideoDemo.mp4](https://1drv.ms/v/c/2bb2f9afc8ae1149/IQCHJjnHzWfAQY05ac-7v-RAAY6GN3OULaFws6Xx1zj3mFE?e=0zF5HR) 🎬 |
| **Public URL**       | https://kwizeragate-app-kwizeragate.apps.itz-7zzjya.hub04-lb.techzone.ibm.com                                                 |
| **Dashboard**        | https://kwizeragate-app-kwizeragate.apps.itz-7zzjya.hub04-lb.techzone.ibm.com/                                                |
| **Swagger API Docs** | https://kwizeragate-app-kwizeragate.apps.itz-7zzjya.hub04-lb.techzone.ibm.com/docs                                            |
| **Health probe**     | `/health` → `{"status":"ok","service":"KwizeraGate","region":"Burundi"}` ✅                                                   |
| **DB seed**          | `TEST-KEY-BIF-2026` merchant created ✅                                                                                       |

### Security Test Results — Live Cluster (5 / 5 PASS)

```
Target: https://kwizeragate-app-kwizeragate.apps.itz-7zzjya.hub04-lb.techzone.ibm.com

[1] Valid auth (Bujumbura IP)              PASS — low_risk, JWT issued
[2] Spoofed IP → IBM Verify step-up        PASS — HTTP 401, biometric push message
[3] Unknown merchant API key               PASS — HTTP 404
[4] Valid BIF transfer + QRadar log        PASS — transaction_id=1, log written
[5] Suspended merchant blocked             PASS — HTTP 403 after QRadar webhook

Results: 5 / 5 passed
```

| Test | Scenario                                                           | Expected                              | Result  |
| ---- | ------------------------------------------------------------------ | ------------------------------------- | ------- |
| [1]  | Merchant authenticates from Bujumbura IP `196.41.0.5` (MTN subnet) | HTTP 200 + JWT                        | ✅ PASS |
| [2]  | Attacker uses foreign IP `8.8.8.8` — IBM Verify triggers step-up   | HTTP 401 + biometric push             | ✅ PASS |
| [3]  | Request with fabricated API key                                    | HTTP 404                              | ✅ PASS |
| [4]  | Authenticated BIF transfer streamed to QRadar SIEM                 | HTTP 200 + `qradar_logs.json` written | ✅ PASS |
| [5]  | QRadar CRE fires suspend webhook → merchant blocked                | HTTP 403 on transfer attempt          | ✅ PASS |

---

## Project Structure

```
KwizeraGate/
├── main.py                   ← FastAPI app + all endpoints
├── database.py               ← SQLAlchemy engine + session
├── models.py                 ← Merchant + Transaction ORM models
├── schemas.py                ← Pydantic request/response schemas
├── db_init.py                ← DB table creation + seed merchant
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env                      ← Your local config (git-ignored)
├── .env.example              ← Template — safe to commit
├── .gitignore
├── qradar_logs.json          ← Auto-created on first transfer
├── kwizeragate.db            ← SQLite dev DB (git-ignored)
├── security/
│   ├── ibm_verify.py         ← Adaptive MFA stub + real API contract
│   ├── qradar.py             ← SIEM log stream stub + real API contract
│   └── jwt_utils.py          ← JWT issuance + verification
├── test_attacks.py           ← End-to-end security scenario tests
└── docs/
    ├── guardium-integration.md
    └── burundi-compliance.md
```

---

## IBM Credential Swap Guide

The application ships with **realistic stub functions** that mirror the real IBM API contracts.
Set `APP_ENV=production` in `.env` and provide the credentials below to activate live IBM calls.

| `.env` Variable            | Where to find it in IBM Console                               |
| -------------------------- | ------------------------------------------------------------- |
| `IBM_VERIFY_TENANT_URL`    | IBM Verify → Administration → Tenant Settings → Tenant URL    |
| `IBM_VERIFY_CLIENT_ID`     | IBM Verify → API Clients → Create Client → Client ID          |
| `IBM_VERIFY_CLIENT_SECRET` | IBM Verify → API Clients → Create Client → Client Secret      |
| `QRADAR_HOST`              | QRadar console URL (e.g. `https://qradar.yourdomain.com`)     |
| `QRADAR_TOKEN`             | QRadar → Admin → Authorized Services → Add Token → Auth Token |

Stubs remain active as a fallback if a live IBM API call fails — no downtime during testing.

---

## Burundi Regulatory Context

KwizeraGate is designed for compliance with Burundi's financial regulatory framework:

- **BRB (Banque de la République du Burundi):** Central bank licensing is required for payment service providers operating on the BurundiPay network. KwizeraGate is middleware — it does not hold funds; it authenticates and audits payment instructions.
- **ARCT (Agence de Régulation et de Contrôle des Télécommunications):** Data protection registration required before consumer-facing launch. KwizeraGate logs are stored locally and in QRadar — no PII is transmitted without encryption.
- **AML/CFT:** All transactions are logged with merchant ID, IP address, amount, and timestamp. Suspicious patterns (rapid back-to-back transfers) are flagged by QRadar rules and trigger automatic merchant suspension.
- **Currency:** All transactions default to **BIF (Burundian Franc)**. EAC cross-border transfers may use `USD` or `EUR`.
- **Tax:** 30% Corporate Income Tax · 18% VAT (verify current rates with OBR before filing).

See [`docs/burundi-compliance.md`](docs/burundi-compliance.md) for full regulatory notes.

---

## Cornerstone Rubric Self-Check

| Criterion                               | Evidence                                                                                                                                                                                                |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Environment & provisioning              | Docker Compose (`docker compose up`) + SQLite local run + **OpenShift TechZone OCPv live deployment** ✅                                                                                                |
| Technical build — Cybersecurity pathway | IBM Verify (adaptive MFA) + IBM QRadar (SIEM) + IBM Guardium (DB security) all integrated                                                                                                               |
| Sector case-study grounding             | BIF currency, BRB licensing, Bujumbura IP ranges, ARCT data rules, AML/CFT logging                                                                                                                      |
| Audience feature implementation         | `/auth` (MFA), `/transfer` (SIEM stream), `/webhook/qradar-suspend` (anomaly response)                                                                                                                  |
| Demo & presentation                     | [KwizeraGate VideoDemo.mp4](https://1drv.ms/v/c/2bb2f9afc8ae1149/IQDM4rV7D6cuQY-ybytREVQQAUzV2fNTKyupLA4L3QvXV3k?e=FjflvJ) · `test_attacks.py` (5/5 PASS on live cluster) · Live Dashboard + Swagger ✅ |
| Documentation / handoff notes           | README, `docs/`, `.env.example`, IBM swap guide                                                                                                                                                         |

---

_KwizeraGate — Zero-Trust Payment Security for BurundiPay · Modus Chora Studio · 2026_
