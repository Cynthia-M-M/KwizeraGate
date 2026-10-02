# IBM Guardium Integration — KwizeraGate

**Author:** Cynthia Moraa · Modus Chora Studio
**Pathway:** Cybersecurity — IBM Guardium (Data Security)
**Applies to:** KwizeraGate production PostgreSQL instance

---

## What IBM Guardium Does in KwizeraGate

IBM Guardium operates as an **external, passive observer** on the PostgreSQL database — it
does not sit in the application code path. It monitors all SQL traffic flowing to/from the
`kwizeragate` database in real time and enforces data-access policies that protect against:

- **Compromised API keys** — a stolen key allows an attacker to call `/transfer`, but if they
  attempt to directly query the database (e.g. dump the entire `transactions` table), Guardium
  blocks and alerts.
- **Insider threats** — a developer with database access could run bulk `SELECT *` queries;
  Guardium logs every query with full context (user, time, rows returned).
- **Data exfiltration** — bulk reads of more than 100 rows trigger an alert and can be
  configured to automatically terminate the session.

---

## Architecture

```
FastAPI app  ──SQL→  PostgreSQL 15 (Docker container)
                          │
                     S-TAP Agent        ← lightweight Guardium agent
                          │
                     Guardium Collector  ← IBM Guardium appliance or Cloud
                          │
                     Policy Engine       ← rules defined below
                          │
               Alert / Block / Audit
```

The **S-TAP (Software Tap)** agent is installed on the host running the PostgreSQL container.
It captures all database traffic at the OS level without modifying the application or database.

---

## Connection Setup (Docker Compose)

### Step 1 — Install the Guardium S-TAP Agent

On the Docker host (the machine running `docker compose up`):

```bash
# Download the S-TAP installer from IBM Fix Central
# Product: IBM Security Guardium
# Package: S-TAP for Linux

chmod +x guard_stap_installer.sh
sudo ./guard_stap_installer.sh \
  --collector-ip <GUARDIUM_COLLECTOR_IP> \
  --db-type POSTGRESQL \
  --db-port 5432
```

### Step 2 — Register the Database

In the Guardium console:

1. Navigate to **Manage → Activity Monitoring → Database Discovery**
2. Add a new datasource:
   - **Host:** `localhost` (or the Docker host IP if running remotely)
   - **Port:** `5432`
   - **DB Name:** `kwizeragate`
   - **DB User:** `kwizera`
   - **Type:** PostgreSQL

### Step 3 — Environment Variables (for documentation)

The following variables are reserved in `.env.example` for future Guardium automation:

| Variable | Purpose |
|---|---|
| `GUARDIUM_COLLECTOR_IP` | IP address of the Guardium Collector appliance |
| `GUARDIUM_STAP_PORT` | S-TAP listener port (default: 16016) |

---

## Policy Rules

Configure the following three rules in the Guardium Policy Builder:

### Rule 1 — Block Bulk Transaction Reads

**Trigger:** Any `SELECT` query on the `transactions` table that returns more than 100 rows
without a `WHERE merchant_id = ?` filter clause.

**Action:** Block query + Alert + Log full query text, client IP, and DB user.

**Rationale:** Legitimate application queries always filter by `merchant_id`. A bulk `SELECT *`
without a merchant filter is characteristic of data exfiltration.

```sql
-- Pattern to flag:
SELECT * FROM transactions;
SELECT id, amount, receiver_wallet FROM transactions LIMIT 10000;

-- Legitimate pattern (should NOT be flagged):
SELECT * FROM transactions WHERE merchant_id = 7;
```

### Rule 2 — Alert on High-Volume Reads

**Trigger:** More than 100 rows returned from the `transactions` table in any single query,
regardless of whether a `WHERE` clause is present.

**Action:** Alert (do not block) + Log to audit trail with row count.

**Rationale:** Even filtered bulk reads could indicate a compromised admin credential.
Alerting (not blocking) preserves legitimate reporting workflows while flagging anomalies.

### Rule 3 — Block DDL on Production Tables

**Trigger:** Any `DROP TABLE`, `TRUNCATE TABLE`, or `ALTER TABLE ... DROP COLUMN` targeting
`transactions` or `merchants`.

**Action:** Block immediately + Critical alert + Page on-call engineer.

**Rationale:** Merchants and transactions are the core ledger. Any destructive DDL outside
a scheduled maintenance window is an indicator of compromise or insider sabotage.

```sql
-- Always blocked:
DROP TABLE transactions;
TRUNCATE TABLE merchants;

-- Permitted (Alembic migrations via maintenance window only):
ALTER TABLE transactions ADD COLUMN ...;
```

---

## Audit Trail

Guardium writes a tamper-evident audit trail for every query, including:

| Field | Description |
|---|---|
| `timestamp` | UTC time of query execution |
| `db_user` | PostgreSQL role that executed the query |
| `client_ip` | IP that connected to Postgres |
| `sql_text` | Full SQL statement |
| `rows_affected` | Number of rows returned or modified |
| `policy_action` | `ALLOWED` / `BLOCKED` / `ALERT` |

This audit trail satisfies BRB (Banque de la République du Burundi) AML/CFT record-keeping
requirements and ARCT data protection audit obligations.

---

## IBM Guardium Resources

- Product documentation: IBM Security Guardium Data Protection
- S-TAP installation guide: IBM Fix Central → Guardium → S-TAP for Linux
- Guardium on IBM Cloud: IBM Cloud → Security → Guardium Insights SaaS

---

*KwizeraGate · IBM Guardium Integration Notes · Modus Chora Studio · 2026*
