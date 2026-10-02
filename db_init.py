"""
KwizeraGate — Database Initializer & Seed Script
Author: Cynthia Moraa · Modus Chora Studio

Run this once to create all tables and insert a seed merchant so the
application is immediately testable without any manual SQL.

Usage:
    python db_init.py
"""

from database import engine, SessionLocal, Base
from models import Merchant

SEED_MERCHANT = {
    "name": "BurundiPay Test Merchant",
    "location": "Bujumbura, Burundi",
    "api_key": "TEST-KEY-BIF-2025",
}


def init_db():
    print("[db_init] Creating tables …")
    Base.metadata.create_all(bind=engine)
    print("[db_init] Tables ready.")

    db = SessionLocal()
    try:
        existing = db.query(Merchant).filter_by(api_key=SEED_MERCHANT["api_key"]).first()
        if existing:
            # Always reset to active so re-runs start clean (e.g. after test_attacks.py suspends it)
            existing.status = "active"
            db.commit()
            print(f"[db_init] Seed merchant already exists (id={existing.id}). Reset to active.")
        else:
            merchant = Merchant(**SEED_MERCHANT)
            db.add(merchant)
            db.commit()
            db.refresh(merchant)
            print(f"[db_init] Seed merchant created: id={merchant.id} api_key={merchant.api_key!r}")
    finally:
        db.close()

    print("[db_init] Done. You can now start the server with: uvicorn main:app --reload")


if __name__ == "__main__":
    init_db()
