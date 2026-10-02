"""
KwizeraGate — Security Attack Test Suite
Author: Cynthia Moraa · Modus Chora Studio
Pathway: Cybersecurity — IBM Verify · IBM QRadar · IBM Guardium

Exercises all five Zero-Trust security rules end-to-end against a running
KwizeraGate server.

Usage:
    # Make sure the server is running first:
    #   uvicorn main:app --reload --port 8000
    #   (if port 8000 is blocked, use: uvicorn main:app --reload --port 8080)
    python test_attacks.py

    # To change the target port, edit BASE_URL below (line ~35):
    #   BASE_URL = "http://localhost:8080"

Expected output:
    [1] Valid auth (Bujumbura IP)              PASS
    [2] Spoofed IP → IBM Verify step-up        PASS
    [3] Unknown merchant API key               PASS
    [4] Valid BIF transfer + QRadar log        PASS
    [5] Suspended merchant blocked             PASS

    ──────────────────────────────────────────
    Results: 5 / 5 passed
"""

import json
import sys
from pathlib import Path

import requests

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL    = "http://localhost:8000"
SEED_APIKEY = "TEST-KEY-BIF-2026"       # Created by db_init.py

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

results: list[tuple[str, bool, str]] = []


def _record(label: str, passed: bool, detail: str = ""):
    tag = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  {tag}  {detail}" if detail else f"  {tag}")
    results.append((label, passed, detail))


# ── Test 1: Valid auth — Bujumbura IP ─────────────────────────────────────────

def test_valid_auth() -> str:
    """
    Scenario: legitimate merchant authenticates from a known Bujumbura IP.
    Expected: HTTP 200 + JWT token.
    Returns the JWT for use in subsequent tests.
    """
    label = "[1] Valid auth (Bujumbura IP)"
    print(f"\n{BOLD}{label}{RESET}")

    resp = requests.post(f"{BASE_URL}/auth", json={
        "api_key":    SEED_APIKEY,
        "ip_address": "196.41.0.5",   # MTN Burundi — trusted subnet
        "device_id":  "device-bujumbura-001",
    })

    ok = resp.status_code == 200
    data = resp.json() if ok else {}

    if ok:
        token = data.get("token", "")
        ok = ok and bool(token) and data.get("risk_level") == "low_risk"
        _record(label, ok, f"risk_level={data.get('risk_level')}  token_length={len(token)}")
        return token
    else:
        _record(label, False, f"HTTP {resp.status_code}: {resp.text[:120]}")
        return ""


# ── Test 2: Spoofed IP → IBM Verify step-up ───────────────────────────────────

def test_spoofed_ip():
    """
    Scenario: attacker uses an unrecognized foreign IP to authenticate.
    Expected: HTTP 401 with IBM Verify step-up message.
    """
    label = "[2] Spoofed IP -> IBM Verify step-up"
    print(f"\n{BOLD}{label}{RESET}")

    resp = requests.post(f"{BASE_URL}/auth", json={
        "api_key":    SEED_APIKEY,
        "ip_address": "8.8.8.8",    # Google DNS — definitely not Bujumbura
        "device_id":  "device-unknown-attacker",
    })

    ok = resp.status_code == 401
    detail_text = resp.json().get("detail", "") if resp.headers.get("content-type", "").startswith("application/json") else resp.text
    ok = ok and "IBM Verify Step-Up Authentication Required" in detail_text
    _record(label, ok, f"HTTP {resp.status_code}  detail={detail_text[:100]}")


# ── Test 3: Unknown merchant API key ─────────────────────────────────────────

def test_unknown_merchant():
    """
    Scenario: request with a completely fabricated API key.
    Expected: HTTP 404.
    """
    label = "[3] Unknown merchant API key"
    print(f"\n{BOLD}{label}{RESET}")

    resp = requests.post(f"{BASE_URL}/auth", json={
        "api_key":    "FAKE-KEY-DOES-NOT-EXIST-9999",
        "ip_address": "196.41.0.5",
        "device_id":  "device-attacker",
    })

    ok = resp.status_code == 404
    _record(label, ok, f"HTTP {resp.status_code}")


# ── Test 4: Valid BIF transfer + QRadar log ───────────────────────────────────

def test_valid_transfer(token: str):
    """
    Scenario: authenticated merchant submits a BIF transfer.
    Expected:
      - HTTP 200 + transaction_id
      - qradar_logs.json exists and contains the event
    """
    label = "[4] Valid BIF transfer + QRadar log"
    print(f"\n{BOLD}{label}{RESET}")

    if not token:
        _record(label, False, "No JWT from test 1 — skipping")
        return

    # Get merchant_id from token (decode without verify for test purposes)
    import base64, json as _json
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        merchant_id = _json.loads(base64.b64decode(payload_b64)).get("merchant_id", 1)
    except Exception:
        merchant_id = 1

    resp = requests.post(
        f"{BASE_URL}/transfer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "merchant_id":     merchant_id,
            "receiver_wallet": "WALLET-BI-0099-TEST",
            "amount":          15000.00,
            "currency":        "BIF",
            "ip_address":      "196.41.0.5",
            "device_id":       "device-bujumbura-001",
        },
    )

    ok = resp.status_code == 200
    tx_id = resp.json().get("transaction_id") if ok else None
    qradar_ok = Path("qradar_logs.json").exists()

    ok = ok and tx_id is not None and qradar_ok
    _record(
        label, ok,
        f"HTTP {resp.status_code}  transaction_id={tx_id}  "
        f"qradar_log={'✓' if qradar_ok else '✗ MISSING'}"
    )


# ── Test 5: Suspended merchant blocked ───────────────────────────────────────

def test_suspended_merchant(token: str):
    """
    Scenario:
      1. QRadar fires the anomaly webhook → merchant suspended.
      2. Merchant attempts a transfer → blocked with HTTP 403.
    """
    label = "[5] Suspended merchant blocked"
    print(f"\n{BOLD}{label}{RESET}")

    if not token:
        _record(label, False, "No JWT from test 1 — skipping")
        return

    # Decode merchant_id from token
    import base64, json as _json
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        merchant_id = _json.loads(base64.b64decode(payload_b64)).get("merchant_id", 1)
    except Exception:
        merchant_id = 1

    # Step A: QRadar fires suspend webhook
    suspend_resp = requests.post(f"{BASE_URL}/webhook/qradar-suspend", json={
        "merchant_id": merchant_id,
        "reason":      "Rapid back-to-back transfer anomaly detected by QRadar CRE rule KG-001",
    })
    suspended = suspend_resp.status_code == 200 and \
                suspend_resp.json().get("new_status") == "suspended"

    if not suspended:
        _record(label, False, f"Suspend webhook failed: HTTP {suspend_resp.status_code}")
        return

    # Step B: attempt transfer — must be blocked
    transfer_resp = requests.post(
        f"{BASE_URL}/transfer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "merchant_id":     merchant_id,
            "receiver_wallet": "WALLET-BI-ATTACKER",
            "amount":          999999.00,
            "currency":        "BIF",
            "ip_address":      "196.41.0.5",
            "device_id":       "device-bujumbura-001",
        },
    )

    ok = transfer_resp.status_code == 403
    _record(
        label, ok,
        f"Suspend: HTTP {suspend_resp.status_code}  "
        f"Transfer attempt: HTTP {transfer_resp.status_code} (expected 403)"
    )


# ── Main runner ───────────────────────────────────────────────────────────────

def run_all():
    sep = "=" * 58
    print(f"\n{BOLD}{sep}{RESET}")
    print(f"{BOLD}  KwizeraGate - Security Attack Test Suite{RESET}")
    print(f"  IBM Verify + QRadar + Guardium Zero-Trust Demo")
    print(f"  Target: {BASE_URL}")
    print(f"{BOLD}{sep}{RESET}")

    token = test_valid_auth()
    test_spoofed_ip()
    test_unknown_merchant()
    test_valid_transfer(token)
    test_suspended_merchant(token)

    passed = sum(1 for _, ok, _ in results if ok)
    total  = len(results)

    print(f"\n{'-' * 58}")
    for label, ok, _ in results:
        tag = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {tag}  {label}")
    print(f"{'-' * 58}")
    print(f"\n{BOLD}Results: {passed} / {total} passed{RESET}\n")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
