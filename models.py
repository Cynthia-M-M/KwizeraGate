"""
KwizeraGate — SQLAlchemy ORM Models
Author: Cynthia Moraa · Modus Chora Studio

Tables:
  - Merchant   : registered payment merchants on BurundiPay
  - Transaction: individual transfer records, all denominated in BIF by default
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from database import Base


class Merchant(Base):
    """
    Registered merchant on the BurundiPay network.

    Fields
    ------
    api_key : unique credential used to authenticate via POST /auth
    status  : 'active' | 'suspended'
              A suspended merchant is blocked from all /transfer requests.
              IBM QRadar triggers suspension via POST /webhook/qradar-suspend.
    """
    __tablename__ = "merchants"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name       = Column(String(120), nullable=False)
    location   = Column(String(120))
    api_key    = Column(String(64), unique=True, nullable=False, index=True)
    status     = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="merchant")

    def __repr__(self):
        return f"<Merchant id={self.id} name={self.name!r} status={self.status!r}>"


class Transaction(Base):
    """
    Individual payment transfer record.

    Fields
    ------
    currency    : defaults to 'BIF' (Burundian Franc).
                  EAC cross-border transfers may use 'USD' or 'EUR'.
    status      : 'pending' | 'approved' | 'blocked'
    risk_level  : result from IBM Verify risk assessment — 'low_risk' | 'high_risk'
    device_id   : device fingerprint submitted with /auth and forwarded here for audit
    """
    __tablename__ = "transactions"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    merchant_id     = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    receiver_wallet = Column(String(80), nullable=False)
    amount          = Column(Numeric(18, 2), nullable=False)
    currency        = Column(String(10), nullable=False, default="BIF")
    status          = Column(String(20), nullable=False, default="pending")
    ip_address      = Column(String(45))
    device_id       = Column(String(120))
    risk_level      = Column(String(20))
    timestamp       = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="transactions")

    def __repr__(self):
        return (
            f"<Transaction id={self.id} merchant_id={self.merchant_id} "
            f"amount={self.amount} {self.currency} status={self.status!r}>"
        )
