"""
KwizeraGate — Pydantic Request / Response Schemas
Author: Cynthia Moraa · Modus Chora Studio

All endpoint I/O is typed through these models.
No raw dict usage in endpoint handlers.
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ── /auth ────────────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    api_key:    str = Field(..., description="Merchant API key issued at registration")
    ip_address: str = Field(..., description="Client IP address for IBM Verify risk check")
    device_id:  str = Field(..., description="Device fingerprint for IBM Verify risk assessment")


class AuthResponse(BaseModel):
    token:      str
    risk_level: str  # 'low_risk' | 'high_risk'
    message:    str


# ── /transfer ────────────────────────────────────────────────────────────────

class TransferRequest(BaseModel):
    merchant_id:     int   = Field(..., description="Merchant database ID")
    receiver_wallet: str   = Field(..., max_length=80, description="Destination mobile wallet address")
    amount:          float = Field(..., gt=0, description="Transfer amount (must be > 0)")
    currency:        Literal["BIF", "USD", "EUR"] = Field(
        default="BIF",
        description="Currency code. Defaults to BIF (Burundian Franc). "
                    "USD/EUR allowed for EAC cross-border transfers."
    )
    ip_address: str = Field(..., description="Origin IP for QRadar SIEM audit log")
    device_id:  str = Field(..., description="Device fingerprint for QRadar SIEM audit log")


class TransferResponse(BaseModel):
    transaction_id: int
    status:         str
    message:        str


# ── /status/{transaction_id} ─────────────────────────────────────────────────

class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:              int
    merchant_id:     int
    receiver_wallet: str
    amount:          float
    currency:        str
    status:          str
    ip_address:      Optional[str]
    device_id:       Optional[str]
    risk_level:      Optional[str]
    timestamp:       Optional[datetime]


# ── /webhook/qradar-suspend ──────────────────────────────────────────────────

class QRadarSuspend(BaseModel):
    merchant_id: int  = Field(..., description="ID of the merchant to suspend")
    reason:      str  = Field(..., description="Human-readable reason logged by QRadar rule")


class QRadarSuspendResp(BaseModel):
    merchant_id: int
    new_status:  str
    message:     str
