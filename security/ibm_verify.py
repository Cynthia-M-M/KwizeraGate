"""
KwizeraGate — IBM Verify Adaptive MFA Integration
Author: Cynthia Moraa · Modus Chora Studio

This module implements risk-based authentication that mirrors the IBM Verify
Security Risk API contract.

STUB MODE  (APP_ENV != "production"):
    Risk is evaluated locally using IP subnet matching.
    - Bujumbura trusted subnets (MTN Burundi, ONATEL Burundi) → 'low_risk'
    - Loopback 127.0.0.1 / ::1                                → 'low_risk'
    - Any other IP                                             → 'high_risk'

PRODUCTION MODE (APP_ENV=production):
    Real IBM Verify REST call is made. Stub is used as fallback on failure.

────────────────────────────────────────────────────────────────────────────────
IBM VERIFY REAL API CONTRACT (for credential swap-in):

    Step 1 — Obtain access token:
        POST https://{IBM_VERIFY_TENANT_URL}/v1.0/endpoint/default/token
        Body (form-encoded):
            grant_type=client_credentials
            &client_id={IBM_VERIFY_CLIENT_ID}
            &client_secret={IBM_VERIFY_CLIENT_SECRET}
        Response: { "access_token": "...", "token_type": "Bearer" }

    Step 2 — Request risk evaluation:
        POST https://{IBM_VERIFY_TENANT_URL}/v1.0/authenticators/risk
        Headers:
            Authorization: Bearer {access_token}
            Content-Type:  application/json
        Body:
            { "ipAddress": "<ip>", "deviceId": "<device_id>" }
        Response:
            { "riskLevel": "LOW" | "MEDIUM" | "HIGH", "factors": [...] }

    Map IBM response → KwizeraGate:
        "LOW"    → "low_risk"
        "MEDIUM" → "low_risk"   (adjust per policy)
        "HIGH"   → "high_risk"
────────────────────────────────────────────────────────────────────────────────
"""

import ipaddress
import os
import logging

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

APP_ENV = os.getenv("APP_ENV", "development")

# Trusted Bujumbura subnets (AFRINIC allocations — verify current assignments)
# 196.41.0.0/16 — MTN Burundi
# 41.186.0.0/16 — ONATEL Burundi
_DEFAULT_TRUSTED_SUBNETS = ["196.41.0.0/16", "41.186.0.0/16"]


def _load_trusted_networks() -> list:
    raw = os.getenv("BUJUMBURA_SUBNETS", ",".join(_DEFAULT_TRUSTED_SUBNETS))
    networks = []
    for cidr in raw.split(","):
        cidr = cidr.strip()
        if cidr:
            try:
                networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                logger.warning("[IBM Verify] Invalid subnet in BUJUMBURA_SUBNETS: %s", cidr)
    return networks


_TRUSTED_NETWORKS = _load_trusted_networks()


def _stub_risk_check(ip_address: str, device_id: str) -> str:
    """
    Local stub that evaluates risk using IP subnet matching.
    Returns 'low_risk' or 'high_risk'.
    """
    loopback = {"127.0.0.1", "::1", "localhost"}
    if ip_address in loopback:
        logger.info("[IBM Verify STUB] %s → low_risk (loopback)", ip_address)
        return "low_risk"

    try:
        addr = ipaddress.ip_address(ip_address)
    except ValueError:
        logger.warning("[IBM Verify STUB] Unparseable IP '%s' → high_risk", ip_address)
        return "high_risk"

    for network in _TRUSTED_NETWORKS:
        if addr in network:
            logger.info("[IBM Verify STUB] %s → low_risk (Bujumbura subnet %s)", ip_address, network)
            return "low_risk"

    logger.info("[IBM Verify STUB] %s → high_risk (unrecognized origin)", ip_address)
    return "high_risk"


def _production_risk_check(ip_address: str, device_id: str) -> str:
    """
    Calls the real IBM Verify risk API.
    Falls back to the stub on any network or API error.
    """
    tenant_url    = os.getenv("IBM_VERIFY_TENANT_URL", "")
    client_id     = os.getenv("IBM_VERIFY_CLIENT_ID", "")
    client_secret = os.getenv("IBM_VERIFY_CLIENT_SECRET", "")

    try:
        # Step 1: obtain access token
        token_resp = requests.post(
            f"{tenant_url}/v1.0/endpoint/default/token",
            data={
                "grant_type":    "client_credentials",
                "client_id":     client_id,
                "client_secret": client_secret,
            },
            timeout=5,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        # Step 2: risk evaluation
        risk_resp = requests.post(
            f"{tenant_url}/v1.0/authenticators/risk",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            json={"ipAddress": ip_address, "deviceId": device_id},
            timeout=5,
        )
        risk_resp.raise_for_status()
        ibm_level = risk_resp.json().get("riskLevel", "HIGH")

        result = "low_risk" if ibm_level in ("LOW", "MEDIUM") else "high_risk"
        logger.info("[IBM Verify LIVE] %s device=%s → %s", ip_address, device_id, result)
        return result

    except Exception as exc:
        logger.error("[IBM Verify LIVE] API call failed (%s) — falling back to stub", exc)
        return _stub_risk_check(ip_address, device_id)


def check_ibm_verify_risk(ip_address: str, device_id: str) -> str:
    """
    Public entry point. Returns 'low_risk' or 'high_risk'.

    Routes to the real IBM Verify API when APP_ENV=production,
    otherwise uses the local subnet stub.
    """
    if APP_ENV == "production":
        return _production_risk_check(ip_address, device_id)
    return _stub_risk_check(ip_address, device_id)
