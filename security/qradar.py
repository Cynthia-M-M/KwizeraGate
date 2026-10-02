"""
KwizeraGate — IBM QRadar SIEM Integration
Author: Cynthia Moraa · Modus Chora Studio

Streams structured transaction events to IBM QRadar for behavioral anomaly
detection. Every /transfer call passes through this module.

STUB MODE  (APP_ENV != "production"):
    Events are written to a local qradar_logs.json file (newline-delimited JSON).
    This simulates a QRadar log-source ingest stream and is readable for demo.

PRODUCTION MODE (APP_ENV=production):
    Real HTTP POST is made to the QRadar REST API.
    Stub is used as fallback on failure.

────────────────────────────────────────────────────────────────────────────────
IBM QRADAR REAL API CONTRACT (for credential swap-in):

    Log Source POST (custom log source):
        POST https://{QRADAR_HOST}/api/siem/log_source_management/log_sources
        Headers:
            SEC: {QRADAR_TOKEN}
            Content-Type: application/json
            Version: 14.0

    Event ingest via syslog or HTTP Event Collector is preferred in production.
    For REST-based ingest, use the Ariel REST API or a Universal DSM log source.

    Minimal event payload structure:
        {
            "log_source":    "KwizeraGate-BurundiPay",
            "event_type":    "PAYMENT_TRANSFER",
            "merchant_id":   123,
            "ip_address":    "196.41.1.5",
            "amount":        50000.00,
            "currency":      "BIF",
            "risk_level":    "low_risk",
            "transaction_id": 42,
            "timestamp":     "2026-07-31T14:22:00Z"
        }

    QRadar Custom Rule Engine (CRE) should flag:
        - More than 5 transfers from the same merchant_id within 60 seconds
        - Any transfer where risk_level = 'high_risk' reaches status 'approved'
        - Amount > 10,000,000 BIF in a single transaction (configurable threshold)
────────────────────────────────────────────────────────────────────────────────
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

APP_ENV       = os.getenv("APP_ENV", "development")
LOG_FILE_PATH = Path("qradar_logs.json")


def _write_stub_log(event: dict) -> None:
    """Appends a JSON event line to the local QRadar stub log file."""
    with LOG_FILE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    logger.info("[QRadar STUB] Event logged to %s — transaction_id=%s", LOG_FILE_PATH, event.get("transaction_id"))


def _post_to_qradar(event: dict) -> None:
    """
    Sends the event to the real IBM QRadar HTTP endpoint.
    Falls back to stub on any error.
    """
    qradar_host  = os.getenv("QRADAR_HOST", "")
    qradar_token = os.getenv("QRADAR_TOKEN", "")

    try:
        resp = requests.post(
            f"{qradar_host}/api/siem/offenses",
            headers={
                "SEC":          qradar_token,
                "Content-Type": "application/json",
                "Version":      "14.0",
            },
            json={"log_source": "KwizeraGate-BurundiPay", "event": event},
            timeout=5,
            verify=True,
        )
        resp.raise_for_status()
        logger.info("[QRadar LIVE] Event accepted — transaction_id=%s", event.get("transaction_id"))
    except Exception as exc:
        logger.error("[QRadar LIVE] POST failed (%s) — falling back to stub log", exc)
        _write_stub_log(event)


def stream_to_qradar(transaction_data: dict) -> None:
    """
    Public entry point — streams a transaction event to QRadar.

    Expected keys in transaction_data:
        transaction_id, merchant_id, ip_address, device_id,
        amount, currency, risk_level, status

    Always stamps the event with a UTC ISO-8601 timestamp.
    """
    event = {
        "log_source":      "KwizeraGate-BurundiPay",
        "event_type":      "PAYMENT_TRANSFER",
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "transaction_id":  transaction_data.get("transaction_id"),
        "merchant_id":     transaction_data.get("merchant_id"),
        "ip_address":      transaction_data.get("ip_address"),
        "device_id":       transaction_data.get("device_id"),
        "amount":          transaction_data.get("amount"),
        "currency":        transaction_data.get("currency", "BIF"),
        "risk_level":      transaction_data.get("risk_level"),
        "status":          transaction_data.get("status"),
    }

    if APP_ENV == "production":
        _post_to_qradar(event)
    else:
        _write_stub_log(event)
