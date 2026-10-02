# KwizeraGate — Build Plan

**Author:** Cynthia Moraa · **Company/Solution:** Modus Chora Studio / KwizeraGate
**Pathway:** Cybersecurity (IBM Guardium · IBM QRadar · IBM Verify)
**Target Region:** Burundi · **Currency:** BIF (Burundian Franc)


---

## Top-Level Overview

KwizeraGate is a cloud-native, Zero-Trust payment entry middleware that secures transactions
across Burundi's Digital Public Infrastructure (DPI) — specifically the BurundiPay mobile
wallet network. It replaces vulnerable SMS-OTP flows with adaptive risk-based authentication
and streams every transaction through a behavioral anomaly engine before routing to the
core payment switch.

### IBM Security Stack
| IBM Tool | Role in KwizeraGate |
|---|---|
| **IBM Verify** | Adaptive MFA — biometric push or step-up auth if IP/device is unrecognized |
| **IBM QRadar** | SIEM log ingestion — real-time JSON transaction streams, anomaly webhooks |
| **IBM Guardium** | SQL ledger monitoring — blocks unauthorized queries / bulk data exfiltration |

### Database Strategy
- **Development:** SQLite (zero-setup, file-based — `kwizeragate.db`)
- **Production / Docker:** PostgreSQL 15 via `docker-compose.yml`
- The `DATABASE_URL` env var switches between both; no code change needed.

### Scope
Build a fully functional MVP (not just a demo) with:
- Real database reads/writes (SQLite locally, Postgres in Docker)
- Real JWT issuance and validation
- Realistic IBM Verify and IBM QRadar stub functions mirroring real API contracts
- A `test_attacks.py` script that exercises all security rules end-to-end
- A `Dockerfile` + `docker-compose.yml` that spins up the full stack

### Out of Scope (Phase 3+)
- Real IBM Cloud account provisioning
- BurundiPay core switch integration
- Frontend / merchant portal UI

---

## Sub-Task 1 — Project Scaffold & Metadata

**Intent:** Establish the project skeleton so every subsequent task has a consistent home.
Creates the header files that satisfy the submission requirement (author, company, IBM stack declared upfront).

**Expected Outcomes:**
- `README.md` with author block, solution name, IBM tech stack, Burundi regulatory context, and "how to swap in real IBM credentials" section
- `.gitignore` tuned for Python + Docker + `.env` files
- `.env.example` listing every required environment variable with safe placeholder values
- `requirements.txt` with all pinned dependencies

**Todo List:**
1. Create `README.md` — opening lines MUST be: author name, solution name, pathway, IBM tools used
2. Add Burundi regulatory context section (BRB licensing, AML/CFT, ARCT data mandate, BIF currency)
3. Add "IBM Credential Swap Guide" section — where each env var maps to which IBM console
4. Create `.gitignore` (Python standard + `.env` + `*.db` + `__pycache__`)
5. Create `.env.example` with variables: `DATABASE_URL`, `SECRET_KEY`, `IBM_VERIFY_TENANT_URL`, `IBM_VERIFY_CLIENT_ID`, `IBM_VERIFY_CLIENT_SECRET`, `QRADAR_HOST`, `QRADAR_TOKEN`, `BUJUMBURA_SUBNET`, `APP_ENV`
6. Create `requirements.txt`: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `psycopg2-binary`, `python-dotenv`, `requests`, `python-jose[cryptography]`, `passlib[bcrypt]`, `pydantic`, `aiofiles`

**Relevant Context:** GitHub reference repo https://github.com/Kijani-Support/IBMxMCStudioProgram.git — README.md structure and compliance flow. Burundi dossier: BRB (central bank), ARCT (telecom/data regulator), 30% CIT, 18% VAT.

**Status:** `[ ] pending`

---

## Sub-Task 2 — Database Layer (SQLAlchemy + SQLite/Postgres dual mode)

**Intent:** Build the data layer so the application has real persistence from day one.
All subsequent tasks write to and read from this layer — it must be solid before endpoints are wired.

**Expected Outcomes:**
- `database.py` that reads `DATABASE_URL` from `.env` and constructs the engine; SQLite for dev, Postgres for production
- `models.py` with two SQLAlchemy ORM models: `Merchant` and `Transaction`, matching the schema below
- Alembic is NOT used (out of scope for MVP) — tables are created via `Base.metadata.create_all()` on startup
- `db_init.py` helper script that seeds one test merchant so the app is immediately usable

**Schema:**

```
Merchant
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  name        VARCHAR(120) NOT NULL
  location    VARCHAR(120)
  api_key     VARCHAR(64) UNIQUE NOT NULL
  status      VARCHAR(20) DEFAULT 'active'   -- 'active' | 'suspended'
  created_at  DATETIME DEFAULT now()

Transaction
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  merchant_id   INTEGER FK → Merchant.id
  receiver_wallet VARCHAR(80) NOT NULL
  amount        NUMERIC(18,2) NOT NULL
  currency      VARCHAR(10) DEFAULT 'BIF'
  status        VARCHAR(20) DEFAULT 'pending'  -- 'pending' | 'approved' | 'blocked'
  ip_address    VARCHAR(45)
  device_id     VARCHAR(120)
  risk_level    VARCHAR(20)   -- 'low_risk' | 'high_risk'
  timestamp     DATETIME DEFAULT now()
```

**Todo List:**
1. Create `database.py` — load `DATABASE_URL` from env, create SQLAlchemy engine with `check_same_thread=False` for SQLite compat, expose `SessionLocal` and `Base`
2. Create `models.py` — define `Merchant` and `Transaction` ORM classes from schema above
3. Create `db_init.py` — call `Base.metadata.create_all()`, then insert seed merchant with known `api_key = "TEST-KEY-BIF-2026"` if not already present
4. Add `get_db()` dependency function to `database.py` for FastAPI dependency injection

**Relevant Context:** `DATABASE_URL` format: `sqlite:///./kwizeragate.db` (dev) vs `postgresql://user:pass@db:5432/kwizeragate` (Docker). SQLite requires `connect_args={"check_same_thread": False}`.

**Status:** `[ ] pending`

---

## Sub-Task 3 — Pydantic Schemas

**Intent:** Define all request/response shapes in one file so every endpoint has typed, validated I/O.
Keeping schemas separate from models avoids circular imports and makes the API contract explicit.

**Expected Outcomes:**
- `schemas.py` with Pydantic v2 models for every endpoint request and response
- No raw `dict` usage anywhere in endpoint handlers

**Schemas to define:**
```
AuthRequest        { api_key: str, ip_address: str, device_id: str }
AuthResponse       { token: str, risk_level: str, message: str }

TransferRequest    { merchant_id: int, receiver_wallet: str, amount: float,
                     currency: str = "BIF", ip_address: str, device_id: str }
TransferResponse   { transaction_id: int, status: str, message: str }

TransactionOut     { id, merchant_id, receiver_wallet, amount, currency,
                     status, ip_address, risk_level, timestamp }

QRadarSuspend      { merchant_id: int, reason: str }
QRadarSuspendResp  { merchant_id: int, new_status: str, message: str }
```

**Todo List:**
1. Create `schemas.py` with all models above using `pydantic.BaseModel`
2. Add `model_config = ConfigDict(from_attributes=True)` to `TransactionOut` for ORM serialization

**Status:** `[ ] pending`

---

## Sub-Task 4 — IBM Verify Integration (Adaptive MFA Stub)

**Intent:** Wire risk-based authentication logic that mirrors the real IBM Verify API contract.
The stub must be realistic enough that swapping in real credentials requires only changing env vars, not logic.

**Expected Outcomes:**
- `security/ibm_verify.py` utility module
- `check_ibm_verify_risk(ip_address, device_id) -> str` returns `"low_risk"` or `"high_risk"`
- Risk rules: Bujumbura subnet (`196.41.x.x`, `41.186.x.x`) and `127.0.0.1` → `low_risk`; everything else → `high_risk`
- Stub logs the decision to console so behavior is visible during testing
- Comment block in the file shows the exact IBM Verify REST call that replaces the stub

**IBM Verify real API contract (documented for swap-in):**
```
POST https://{IBM_VERIFY_TENANT_URL}/v1.0/authenticators/risk
Headers: Authorization: Bearer {token}
Body: { "ipAddress": "...", "deviceId": "..." }
Response: { "riskLevel": "LOW" | "HIGH", "factors": [...] }
```

**Todo List:**
1. Create `security/` package with `__init__.py`
2. Create `security/ibm_verify.py` with `check_ibm_verify_risk()` stub function
3. Include Bujumbura subnet list (two real Burundian IP ranges from AFRINIC allocations)
4. Add `APP_ENV` guard: if `APP_ENV=production`, attempt real IBM Verify call; fall back to stub on failure
5. Create `security/jwt_utils.py` — `create_access_token(data: dict) -> str` using `python-jose` and `SECRET_KEY` env var; include `exp` claim (30 min)

**Relevant Context:** Real Bujumbura IP ranges: `196.41.0.0/16` (MTN Burundi), `41.186.0.0/16` (ONATEL Burundi). JWT secret loaded from `.env` `SECRET_KEY`.

**Status:** `[ ] pending`

---

## Sub-Task 5 — IBM QRadar Integration (SIEM Log Stream Stub)

**Intent:** Establish the behavioral monitoring pipeline so every transfer is logged and anomaly webhooks work end-to-end.

**Expected Outcomes:**
- `security/qradar.py` utility module
- `stream_to_qradar(transaction_data: dict)` writes a structured JSON log entry to `qradar_logs.json` (append mode), mirroring a real QRadar log-source POST
- Log entry includes: `timestamp`, `event_type`, `merchant_id`, `ip_address`, `amount`, `risk_level`, `transaction_id`
- Comment block documents the real QRadar Syslog/REST API call for swap-in

**QRadar real API contract (documented for swap-in):**
```
POST https://{QRADAR_HOST}/api/siem/offenses
Headers: SEC: {QRADAR_TOKEN}, Content-Type: application/json
Body: { "log_source": "KwizeraGate", "event": {...} }
```

**Todo List:**
1. Create `security/qradar.py` with `stream_to_qradar()` stub
2. Ensure `qradar_logs.json` is created if it does not exist
3. Add `APP_ENV` guard for real QRadar POST (same pattern as IBM Verify)

**Status:** `[ ] pending`

---

## Sub-Task 6 — FastAPI Application & Endpoints

**Intent:** Build the core API with all five endpoints fully wired to the database and security layers.

**Expected Outcomes:**
- `main.py` with a working FastAPI app
- `Base.metadata.create_all()` called on startup so the DB is auto-initialized
- All five endpoints functional and returning correct HTTP status codes

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| POST | `/auth` | Accept `api_key` + `ip_address` + `device_id`; validate merchant exists; call IBM Verify stub; return JWT if low_risk, 401 if high_risk |
| POST | `/transfer` | Accept transfer payload; verify merchant is not suspended; save transaction; call QRadar stub; return transaction ID |
| GET | `/status/{transaction_id}` | Return full `TransactionOut` for the given ID |
| POST | `/webhook/qradar-suspend` | Accept `merchant_id` + `reason`; set merchant `status = 'suspended'`; return confirmation |
| GET | `/health` | Returns `{ "status": "ok", "service": "KwizeraGate" }` — used by Docker health check |

**Security rules enforced:**
- `/transfer` checks merchant `status != 'suspended'` before processing; returns 403 if suspended
- `/auth` validates `api_key` against the Merchant table; returns 404 if unknown
- JWT from `/auth` is required on `/transfer` (Bearer token header) via a FastAPI dependency

**Todo List:**
1. Create `main.py` — initialize FastAPI with `title="KwizeraGate"`, `description`, and `version`
2. Call `create_all()` inside a `lifespan` startup handler
3. Implement `POST /auth` with IBM Verify risk check and JWT issuance
4. Implement `POST /transfer` with suspended-merchant guard and QRadar stream
5. Implement `GET /status/{transaction_id}`
6. Implement `POST /webhook/qradar-suspend`
7. Implement `GET /health`
8. Add CORS middleware (allow all origins for dev)
9. Add `verify_token()` FastAPI dependency using `security/jwt_utils.py`

**Relevant Context:** FastAPI `Depends(get_db)` for database sessions; `Depends(verify_token)` for protected routes. Merchant lookup by `api_key` field, not `id`, on `/auth`.

**Status:** `[ ] pending`

---

## Sub-Task 7 — Containerization (Dockerfile + docker-compose)

**Intent:** Package the application so any reviewer can spin up the full stack with one command (`docker compose up`), using PostgreSQL as the production database.

**Expected Outcomes:**
- `Dockerfile` using `python:3.11-slim`, no cache pip install, exposes port 8000
- `docker-compose.yml` with two services: `app` (FastAPI) and `db` (PostgreSQL 15)
- `DATABASE_URL` in `docker-compose.yml` points to the Postgres container
- `app` service depends on `db` with a health check
- Volume defined for Postgres data persistence

**Todo List:**
1. Create `Dockerfile` — multi-stage not required; use slim base, copy `requirements.txt` first for layer caching, then copy source
2. Create `docker-compose.yml` — services: `db` (postgres:15-alpine, volume, healthcheck) and `app` (build: ., env_file: .env, depends_on with condition `service_healthy`, port 8000:8000)
3. Create `.env` file (actual, not example) with safe local dev defaults — `DATABASE_URL=sqlite:///./kwizeragate.db` for native run, and note inside the file to change for Docker

**Status:** `[ ] pending`

---

## Sub-Task 8 — Security Attack Test Suite

**Intent:** Provide a runnable `test_attacks.py` that proves every security rule works — this is what gets demoed in the live 10–15 min walkthrough.

**Expected Outcomes:**
- `test_attacks.py` using only the `requests` library (no pytest required)
- Covers 5 attack scenarios with clear PASS/FAIL console output
- Can be run against the local server (`http://localhost:8000`) or the Docker stack

**Test scenarios:**
1. **Valid auth** — known `api_key` + Bujumbura IP → expects 200 + JWT token
2. **Spoofed IP auth** — known `api_key` + unknown IP → expects 401 + "IBM Verify Step-Up Authentication Required" message
3. **Unknown merchant auth** — bad `api_key` → expects 404
4. **Valid transfer** — uses JWT from test 1, sends BIF transfer → expects 200 + transaction ID; verifies `qradar_logs.json` was written
5. **Suspended merchant transfer** — trigger `/webhook/qradar-suspend`, then attempt transfer → expects 403

**Todo List:**
1. Create `test_attacks.py` with `BASE_URL = "http://localhost:8000"` configurable at top
2. Implement each of the 5 test functions with `assert` statements and `print("PASS"/"FAIL")` output
3. Add a `run_all()` main block that prints a summary table

**Status:** `[ ] pending`

---

## Sub-Task 9 — IBM Guardium Documentation & Integration Notes

**Intent:** IBM Guardium operates as an external observer on the database — it is not coded into the app. This sub-task documents exactly how it connects to the PostgreSQL instance so the submission fully satisfies the Cybersecurity pathway requirement.

**Expected Outcomes:**
- `docs/guardium-integration.md` explaining: what Guardium monitors, which SQL patterns it flags, how it connects to the Postgres container, and what the `GUARDIUM_` env vars are for
- A "Guardium policy rules" section describing the three rules to configure: block `SELECT *` on `Transaction` without a merchant filter, alert on bulk reads > 100 rows, block any DROP/TRUNCATE on production tables

**Todo List:**
1. Create `docs/` directory
2. Create `docs/guardium-integration.md` with connection instructions, policy rule descriptions, and the IBM Guardium S-TAP agent setup note for the Docker Postgres container

**Status:** `[ ] pending`

---

## Sub-Task 10 — Regulatory Compliance Notes (Burundi)

**Intent:** The submission must be grounded in the actual sector case study — generic fintech apps score 2/4 on "Sector case-study grounding." This task encodes Burundi-specific compliance directly into the project.

**Expected Outcomes:**
- `docs/burundi-compliance.md` covering: BRB (Banque de la République du Burundi) payment licensing requirement, ARCT data protection registration, AML/CFT obligations, BIF currency handling in the Transaction model, EAC cross-border data flow notes
- The `Transaction.currency` field defaults to `"BIF"` and is validated to accept `BIF`, `USD`, `EUR` only (EAC cross-border use cases)

**Todo List:**
1. Create `docs/burundi-compliance.md` based on the Burundi dossier provided
2. Add `currency` field validation in `schemas.py` `TransferRequest` — `Literal["BIF", "USD", "EUR"]`

**Status:** `[ ] pending`

---

## File Structure (Final)

```
KwizeraGate/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── db_init.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
├── README.md
├── qradar_logs.json          ← auto-created at first transfer
├── kwizeragate.db            ← auto-created (dev only, git-ignored)
├── security/
│   ├── __init__.py
│   ├── ibm_verify.py
│   ├── qradar.py
│   └── jwt_utils.py
├── test_attacks.py
└── docs/
    ├── guardium-integration.md
    └── burundi-compliance.md
```

---

## IBM Credential Swap Guide (Summary)

| `.env` Variable | IBM Console Location |
|---|---|
| `IBM_VERIFY_TENANT_URL` | IBM Verify → Administration → Tenant Settings → Tenant URL |
| `IBM_VERIFY_CLIENT_ID` | IBM Verify → API Clients → Create Client → Client ID |
| `IBM_VERIFY_CLIENT_SECRET` | same as above → Client Secret |
| `QRADAR_TOKEN` | QRadar → Admin → Authorized Services → Add Token |
| `QRADAR_HOST` | QRadar console URL (e.g. `https://qradar.yourdomain.com`) |

Set `APP_ENV=production` in `.env` to activate real IBM API calls. The stubs become the fallback.

---

## Rubric Self-Check

| Criterion | How KwizeraGate satisfies it |
|---|---|
| Environment & provisioning | Docker Compose spins full stack; SQLite for instant local run |
| Technical build — pathway fit | IBM Verify, QRadar, Guardium all present and documented |
| Sector case-study grounding | BIF currency, BRB licensing, Bujumbura IP ranges, ARCT data rules |
| Audience feature implementation | `/auth` (adaptive MFA), `/transfer` (SIEM stream), `/webhook` (anomaly suspend) all functional |
| Demo & presentation | [KwizeraGate VideoDemo.mp4](https://1drv.ms/v/c/2bb2f9afc8ae1149/IQCHJjnHzWfAQY05ac-7v-RAAY6GN3OULaFws6Xx1zj3mFE?e=0zF5HR) · `test_attacks.py` produces live PASS/FAIL output for the walkthrough |
| Documentation / handoff notes | README, docs/, `.env.example`, IBM swap guide — another team can pick this up |
