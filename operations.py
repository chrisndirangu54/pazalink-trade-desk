"""Sandbox-only persistent operations API; never a system of record for real money."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ops", tags=["sandbox-operations"])


def database_path():
    return os.getenv("PAZALINK_DB_PATH", "pazalink-demo.sqlite3")


@contextmanager
def db():
    conn = sqlite3.connect(database_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            counterparty TEXT NOT NULL,
            amount TEXT NOT NULL,
            currency TEXT NOT NULL,
            corridor TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            invoice_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            event_id TEXT PRIMARY KEY,
            received_at TEXT NOT NULL
        );
        """)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def principal(authorization: str | None = Header(default=None)):
    """Static server-side user tokens for controlled testing only."""
    raw = os.getenv("PAZALINK_DEMO_TOKENS", "")
    # comma-separated user:token pairs; never expose this config to browsers
    identities = [x.partition(":") for x in raw.split(",") if ":" in x]
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    provided = authorization[7:]
    for user, _, token in identities:
        if user and len(token) >= 24 and hmac.compare_digest(provided, token):
            return user
    raise HTTPException(401, "Invalid bearer token")


class InvoiceCreate(BaseModel):
    counterparty: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=Decimal("0"), le=Decimal("1000000"), decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    corridor: str = Field(min_length=1, max_length=100)


class Transition(BaseModel):
    status: str = Field(pattern=r"^(review|approved|rejected|sandbox-paid)$")
    reason: str = Field(min_length=3, max_length=300)


@router.post("/invoices", status_code=201)
def create_invoice(payload: InvoiceCreate, user: str = Depends(principal)):
    identifier = "PL-" + secrets.token_hex(8).upper()
    stamp = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        conn.execute(
            "INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (identifier, user, payload.counterparty, str(payload.amount),
             payload.currency, payload.corridor, "draft", stamp)
        )
        conn.execute(
            "INSERT INTO events(owner,invoice_id,kind,detail,created_at) VALUES(?,?,?,?,?)",
            (user, identifier, "created", "Created fictional sandbox invoice", stamp)
        )
    return {"id": identifier, "status": "draft", "sandbox_only": True}


@router.get("/invoices")
def list_invoices(user: str = Depends(principal)):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM invoices WHERE owner=? ORDER BY created_at DESC LIMIT 100", (user,)
        ).fetchall()
    return {"items": [dict(row) for row in rows], "sandbox_only": True}


@router.post("/invoices/{invoice_id}/transition")
def transition(invoice_id: str, payload: Transition, user: str = Depends(principal)):
    with db() as conn:
        record = conn.execute(
            "SELECT * FROM invoices WHERE id=? AND owner=?", (invoice_id, user)
        ).fetchone()
        if not record:
            raise HTTPException(404, "Invoice not found")
        current = record["status"]
        allowed = {
            "draft": {"review"},
            "review": {"approved", "rejected"},
            "approved": {"sandbox-paid", "rejected"},
            "rejected": set(),
            "sandbox-paid": set()
        }
        if payload.status not in allowed[current]:
            raise HTTPException(409, "Invalid sandbox state transition")
        # No transition invokes PSPs. 'sandbox-paid' is a manual DEMO marker only.
        conn.execute("UPDATE invoices SET status=? WHERE id=? AND owner=?",
                     (payload.status, invoice_id, user))
        conn.execute(
            "INSERT INTO events(owner,invoice_id,kind,detail,created_at) VALUES(?,?,?,?,?)",
            (user, invoice_id, "transition:" + payload.status, payload.reason,
             datetime.now(timezone.utc).isoformat())
        )
    return {"id": invoice_id, "status": payload.status, "verified_payment": False}


@router.get("/invoices/{invoice_id}/events")
def invoice_events(invoice_id: str, user: str = Depends(principal)):
    with db() as conn:
        owner = conn.execute("SELECT owner FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not owner or owner["owner"] != user:
            raise HTTPException(404, "Invoice not found")
        rows = conn.execute(
            "SELECT id,kind,detail,created_at FROM events WHERE invoice_id=? AND owner=? ORDER BY id",
            (invoice_id, user)
        ).fetchall()
    return {"events": [dict(row) for row in rows]}


@router.get("/integrations")
def integration_status(user: str = Depends(principal)):
    return {
        "owner": user,
        "paypal": "sandbox-adapter-in-app",
        "nebius": "optional-model-adapter-in-app",
        "africas_talking": "not-connected",
        "daraja_mpesa": "not-connected",
        "foreign_exchange": "not-connected",
        "escrow": "not-connected",
        "odoo": "not-connected",
        "production_settlement": False,
    }
