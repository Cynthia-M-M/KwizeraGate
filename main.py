"""
KwizeraGate — FastAPI Application
Author:   Cynthia Moraa · Modus Chora Studio
Pathway:  Cybersecurity — IBM Verify · IBM QRadar · IBM Guardium
Solution: Zero-Trust Payment Entry Middleware for BurundiPay (Burundi DPI)

Endpoints
---------
POST /auth                  — Adaptive MFA via IBM Verify; issues JWT on success
POST /transfer              — Authenticated BIF payment transfer; streams to QRadar
GET  /status/{tx_id}        — Retrieve transaction record
POST /webhook/qradar-suspend— QRadar anomaly webhook; suspends merchant
GET  /health                — Docker/k8s health probe
"""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Merchant, Transaction
from schemas import (
    AuthRequest, AuthResponse,
    QRadarSuspend, QRadarSuspendResp,
    TransactionOut, TransferRequest, TransferResponse,
)
from security.ibm_verify import check_ibm_verify_risk
from security.jwt_utils import create_access_token, verify_token
from security.qradar import stream_to_qradar


# ── Application lifecycle ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all DB tables on startup (idempotent — safe to call every boot)."""
    Base.metadata.create_all(bind=engine)
    yield


# ── FastAPI instance ─────────────────────────────────────────────────────────

app = FastAPI(
    title="KwizeraGate",
    description=(
        "Zero-Trust Payment Entry Middleware for BurundiPay.\n\n"
        "**Author:** Cynthia Moraa · Modus Chora Studio\n"
        "**Pathway:** Cybersecurity — IBM Verify · IBM QRadar · IBM Guardium\n"
        "**Region:** Burundi · **Currency:** BIF (Burundian Franc)"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
_allow_origins = [o.strip() for o in _raw_origins.split(",")] if _raw_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,   # Set ALLOWED_ORIGINS=https://merchant.example.com in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Root dashboard ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(db: Session = Depends(get_db)):
    """Browser-facing dashboard — shows live system status and recent transactions."""
    # Pull last 10 transactions for display
    recent_txs = db.query(Transaction).order_by(Transaction.id.desc()).limit(10).all()
    total_txs  = db.query(Transaction).count()
    merchants  = db.query(Merchant).count()
    suspended  = db.query(Merchant).filter_by(status="suspended").count()

    tx_rows = ""
    for tx in recent_txs:
        status_color = {
            "pending":  "#f59e0b",
            "approved": "#10b981",
            "blocked":  "#ef4444",
        }.get(tx.status, "#6b7280")
        risk_color = "#ef4444" if tx.risk_level == "high_risk" else "#10b981"
        tx_rows += f"""
        <tr>
          <td>#{tx.id}</td>
          <td>{tx.merchant_id}</td>
          <td>{tx.receiver_wallet}</td>
          <td>{float(tx.amount):,.2f} {tx.currency}</td>
          <td><span style="color:{status_color};font-weight:600">{tx.status.upper()}</span></td>
          <td><span style="color:{risk_color};font-size:12px">{tx.risk_level or "—"}</span></td>
          <td style="color:#6b7280;font-size:12px">{str(tx.timestamp)[:19] if tx.timestamp else "—"}</td>
        </tr>"""

    if not tx_rows:
        tx_rows = '<tr><td colspan="7" style="text-align:center;color:#6b7280;padding:32px">No transactions yet. Run test_attacks.py to generate data.</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>KwizeraGate — Zero-Trust Payment Security</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,"Segoe UI",system-ui,sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh}}
    .topbar{{background:#1e2130;border-bottom:1px solid #2d3148;padding:14px 32px;display:flex;align-items:center;justify-content:space-between}}
    .logo{{display:flex;align-items:center;gap:12px}}
    .logo-icon{{width:36px;height:36px;background:linear-gradient(135deg,#3b82f6,#6366f1);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:800;color:#fff}}
    .logo-text{{font-size:18px;font-weight:700;color:#f1f5f9}}
    .logo-sub{{font-size:12px;color:#64748b;margin-top:1px}}
    .badge{{background:#1d4ed8;color:#bfdbfe;font-size:11px;padding:3px 10px;border-radius:20px;font-weight:600}}
    .live{{display:flex;align-items:center;gap:6px;font-size:13px;color:#10b981}}
    .live-dot{{width:8px;height:8px;background:#10b981;border-radius:50%;animation:pulse 2s infinite}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
    .main{{padding:32px}}
    .page-title{{font-size:22px;font-weight:700;color:#f1f5f9;margin-bottom:4px}}
    .page-sub{{font-size:14px;color:#64748b;margin-bottom:28px}}
    .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px}}
    .stat{{background:#1e2130;border:1px solid #2d3148;border-radius:12px;padding:20px}}
    .stat-label{{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}}
    .stat-value{{font-size:32px;font-weight:700;color:#f1f5f9}}
    .stat-sub{{font-size:12px;color:#64748b;margin-top:4px}}
    .ibm-stack{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:28px}}
    .ibm-card{{background:#1e2130;border:1px solid #2d3148;border-radius:12px;padding:20px}}
    .ibm-card-header{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}
    .ibm-icon{{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff}}
    .ibm-icon.verify{{background:#1d4ed8}}
    .ibm-icon.qradar{{background:#7c3aed}}
    .ibm-icon.guardium{{background:#0891b2}}
    .ibm-card-name{{font-size:14px;font-weight:600;color:#f1f5f9}}
    .ibm-card-product{{font-size:11px;color:#64748b}}
    .ibm-status{{display:flex;align-items:center;gap:6px;font-size:12px;margin-top:8px}}
    .ibm-dot{{width:6px;height:6px;border-radius:50%}}
    .ibm-dot.active{{background:#10b981}}
    .ibm-dot.stub{{background:#f59e0b}}
    .ibm-desc{{font-size:13px;color:#94a3b8;line-height:1.5;margin-top:10px}}
    .section-title{{font-size:16px;font-weight:600;color:#f1f5f9;margin-bottom:14px}}
    .table-wrap{{background:#1e2130;border:1px solid #2d3148;border-radius:12px;overflow:hidden}}
    table{{width:100%;border-collapse:collapse;font-size:13px}}
    thead tr{{background:#151824}}
    th{{padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#64748b;font-weight:600}}
    td{{padding:12px 16px;border-top:1px solid #2d3148;color:#cbd5e1}}
    tr:hover td{{background:#232740}}
    .endpoints{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:28px}}
    .ep{{background:#1e2130;border:1px solid #2d3148;border-radius:10px;padding:14px 16px;display:flex;align-items:flex-start;gap:12px}}
    .method{{font-size:11px;font-weight:700;padding:3px 8px;border-radius:5px;white-space:nowrap;margin-top:1px}}
    .method.post{{background:#1d4ed820;color:#60a5fa;border:1px solid #1d4ed840}}
    .method.get{{background:#06652020;color:#34d399;border:1px solid #06652040}}
    .ep-path{{font-size:13px;font-weight:600;color:#f1f5f9;margin-bottom:3px}}
    .ep-desc{{font-size:12px;color:#64748b}}
    .footer{{text-align:center;padding:24px;color:#334155;font-size:12px;border-top:1px solid #1e2130;margin-top:16px}}
    .docs-link{{display:inline-block;margin-top:12px;padding:8px 20px;background:#1d4ed8;color:#fff;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600}}
    .docs-link:hover{{background:#2563eb}}
  </style>
</head>
<body>
  <div class="topbar">
    <div class="logo">
      <div class="logo-icon">K</div>
      <div>
        <div class="logo-text">KwizeraGate</div>
        <div class="logo-sub">Zero-Trust Payment Middleware · BurundiPay</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:16px">
      <span class="badge">IBM Cybersecurity Pathway</span>
      <div class="live"><div class="live-dot"></div>System Online</div>
    </div>
  </div>

  <div class="main">
    <div class="page-title">Security Operations Dashboard</div>
    <div class="page-sub">Author: Cynthia Moraa · Modus Chora Studio · Burundi DPI · BIF Currency</div>

    <!-- Stats -->
    <div class="stats">
      <div class="stat">
        <div class="stat-label">Total Transactions</div>
        <div class="stat-value">{total_txs}</div>
        <div class="stat-sub">All time</div>
      </div>
      <div class="stat">
        <div class="stat-label">Active Merchants</div>
        <div class="stat-value">{merchants - suspended}</div>
        <div class="stat-sub">{suspended} suspended by QRadar</div>
      </div>
      <div class="stat">
        <div class="stat-label">Suspended</div>
        <div class="stat-value" style="color:#ef4444">{suspended}</div>
        <div class="stat-sub">QRadar anomaly blocks</div>
      </div>
      <div class="stat">
        <div class="stat-label">Auth Mode</div>
        <div class="stat-value" style="font-size:22px">Zero-Trust</div>
        <div class="stat-sub">JWT + IBM Verify MFA</div>
      </div>
    </div>

    <!-- IBM Security Stack -->
    <div class="section-title">IBM Security Stack</div>
    <div class="ibm-stack">
      <div class="ibm-card">
        <div class="ibm-card-header">
          <div class="ibm-icon verify">V</div>
          <div>
            <div class="ibm-card-name">IBM Verify</div>
            <div class="ibm-card-product">Identity &amp; Access Management</div>
          </div>
        </div>
        <div class="ibm-status"><div class="ibm-dot stub"></div><span style="color:#f59e0b">Stub Active — swap APP_ENV=production for live</span></div>
        <div class="ibm-desc">Adaptive MFA — evaluates IP &amp; device fingerprint. Bujumbura subnets (MTN 196.41.x.x, ONATEL 41.186.x.x) = low_risk. Unknown IPs trigger biometric push.</div>
      </div>
      <div class="ibm-card">
        <div class="ibm-card-header">
          <div class="ibm-icon qradar">Q</div>
          <div>
            <div class="ibm-card-name">IBM QRadar</div>
            <div class="ibm-card-product">SIEM &amp; Threat Detection</div>
          </div>
        </div>
        <div class="ibm-status"><div class="ibm-dot stub"></div><span style="color:#f59e0b">Logging to qradar_logs.json — swap APP_ENV=production for live</span></div>
        <div class="ibm-desc">Every transfer streamed as a structured JSON event. Custom Rule Engine fires /webhook/qradar-suspend to auto-block anomalous merchants.</div>
      </div>
      <div class="ibm-card">
        <div class="ibm-card-header">
          <div class="ibm-icon guardium">G</div>
          <div>
            <div class="ibm-card-name">IBM Guardium</div>
            <div class="ibm-card-product">Data Security</div>
          </div>
        </div>
        <div class="ibm-status"><div class="ibm-dot active"></div><span style="color:#10b981">External observer — see docs/guardium-integration.md</span></div>
        <div class="ibm-desc">S-TAP agent monitors all PostgreSQL traffic. Blocks bulk SELECT *, DDL on production tables, and unauthorized bulk reads &gt;100 rows.</div>
      </div>
    </div>

    <!-- API Endpoints -->
    <div class="section-title">API Endpoints</div>
    <div class="endpoints" style="margin-bottom:28px">
      <div class="ep"><span class="method post">POST</span><div><div class="ep-path">/auth</div><div class="ep-desc">Adaptive MFA — IBM Verify risk check, JWT issuance</div></div></div>
      <div class="ep"><span class="method post">POST</span><div><div class="ep-path">/transfer</div><div class="ep-desc">BIF payment transfer — QRadar SIEM stream, JWT required</div></div></div>
      <div class="ep"><span class="method get">GET</span><div><div class="ep-path">/status/{{id}}</div><div class="ep-desc">Retrieve transaction details</div></div></div>
      <div class="ep"><span class="method post">POST</span><div><div class="ep-path">/webhook/qradar-suspend</div><div class="ep-desc">QRadar anomaly webhook — suspend merchant</div></div></div>
      <div class="ep"><span class="method get">GET</span><div><div class="ep-path">/health</div><div class="ep-desc">Docker / k8s health probe</div></div></div>
      <div class="ep"><span class="method get">GET</span><div><div class="ep-path">/docs</div><div class="ep-desc">Interactive Swagger API documentation</div></div></div>
    </div>

    <!-- Transactions table -->
    <div class="section-title">Recent Transactions (last 10)</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>Merchant</th><th>Wallet</th><th>Amount</th><th>Status</th><th>Risk</th><th>Time (UTC)</th></tr></thead>
        <tbody>{tx_rows}</tbody>
      </table>
    </div>

    <div style="text-align:center;margin-top:24px">
      <a class="docs-link" href="/docs">Open Interactive API Docs (Swagger)</a>
    </div>
  </div>

  <div class="footer">
    KwizeraGate · Zero-Trust Payment Security for BurundiPay · Modus Chora Studio · 2026<br/>
    IBM Cybersecurity Pathway — IBM Verify · IBM QRadar · IBM Guardium
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)


# ── Health probe ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """Used by Docker Compose health check and load-balancer probes."""
    return {"status": "ok", "service": "KwizeraGate", "region": "Burundi"}


# ── POST /auth ───────────────────────────────────────────────────────────────

@app.post("/auth", response_model=AuthResponse, tags=["Authentication"])
def authenticate(payload: AuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate a merchant and issue a JWT.

    1. Validates api_key against the Merchant table.
    2. Calls IBM Verify (stub or live) to assess IP/device risk.
    3. Returns a signed JWT (30 min) on low_risk.
    4. Returns HTTP 401 with IBM Verify step-up message on high_risk.
    """
    merchant = db.query(Merchant).filter_by(api_key=payload.api_key).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant API key not found. Contact BurundiPay support.",
        )

    if merchant.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Merchant account (id={merchant.id}) is suspended. "
                "Contact BurundiPay compliance."
            ),
        )

    risk_level = check_ibm_verify_risk(payload.ip_address, payload.device_id)

    if risk_level == "high_risk":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="IBM Verify Step-Up Authentication Required: Biometric Push Sent",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": payload.api_key, "merchant_id": merchant.id}
    )
    return AuthResponse(
        token=token,
        risk_level=risk_level,
        message=f"Authentication successful. Welcome, {merchant.name}.",
    )


# ── POST /transfer ───────────────────────────────────────────────────────────

@app.post(
    "/transfer",
    response_model=TransferResponse,
    tags=["Payments"],
    dependencies=[Depends(verify_token)],
)
def transfer(
    payload: TransferRequest,
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token),
):
    """
    Submit a BIF payment transfer.

    - Requires a valid Bearer JWT from POST /auth.
    - Blocks suspended merchants (HTTP 403).
    - Saves the transaction as 'pending'.
    - Streams event to IBM QRadar SIEM.
    """
    merchant = db.query(Merchant).filter_by(id=payload.merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant id={payload.merchant_id} not found.",
        )

    if merchant.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Merchant account (id={merchant.id}) has been suspended by IBM QRadar "
                "anomaly detection. All transfers are blocked."
            ),
        )

    # Persist transaction with 'pending' status
    tx = Transaction(
        merchant_id=payload.merchant_id,
        receiver_wallet=payload.receiver_wallet,
        amount=payload.amount,
        currency=payload.currency,
        status="pending",
        ip_address=payload.ip_address,
        device_id=payload.device_id,
        risk_level=None,   # set after further QRadar analysis if needed
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # Stream to IBM QRadar SIEM
    stream_to_qradar({
        "transaction_id": tx.id,
        "merchant_id":    tx.merchant_id,
        "ip_address":     tx.ip_address,
        "device_id":      tx.device_id,
        "amount":         float(tx.amount),
        "currency":       tx.currency,
        "risk_level":     tx.risk_level,
        "status":         tx.status,
    })

    return TransferResponse(
        transaction_id=tx.id,
        status=tx.status,
        message=(
            f"Transfer of {tx.amount} {tx.currency} to wallet "
            f"{tx.receiver_wallet!r} queued. QRadar monitoring active."
        ),
    )


# ── GET /status/{transaction_id} ─────────────────────────────────────────────

@app.get(
    "/status/{transaction_id}",
    response_model=TransactionOut,
    tags=["Payments"],
    dependencies=[Depends(verify_token)],
)
def get_status(transaction_id: int, db: Session = Depends(get_db)):
    """
    Retrieve the current status and details of a transaction.
    Requires a valid Bearer JWT.
    """
    tx = db.query(Transaction).filter_by(id=transaction_id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction id={transaction_id} not found.",
        )
    return tx


# ── POST /webhook/qradar-suspend ─────────────────────────────────────────────

@app.post("/webhook/qradar-suspend", response_model=QRadarSuspendResp, tags=["Security Webhooks"])
def qradar_suspend(payload: QRadarSuspend, db: Session = Depends(get_db)):
    """
    IBM QRadar anomaly webhook — suspends a merchant session.

    In production this endpoint is called automatically by a QRadar
    Custom Rule Engine (CRE) action when a behavioral anomaly is detected
    (e.g. rapid back-to-back transfers, high-risk IP reaching 'approved').

    After suspension, all further /auth and /transfer requests from this
    merchant return HTTP 403.
    """
    merchant = db.query(Merchant).filter_by(id=payload.merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant id={payload.merchant_id} not found.",
        )

    merchant.status = "suspended"
    db.commit()
    db.refresh(merchant)

    return QRadarSuspendResp(
        merchant_id=merchant.id,
        new_status=merchant.status,
        message=(
            f"Merchant '{merchant.name}' (id={merchant.id}) has been suspended. "
            f"Reason logged by QRadar: {payload.reason}"
        ),
    )
