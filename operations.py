"""Firebase-backed, tenant-isolated DEMO invoice operations (not a payment ledger)."""
from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal

import firebase_admin
from firebase_admin import auth, firestore
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ops", tags=["sandbox-operations"])
ALLOWED = {
    "draft": {"review"},
    "review": {"approved", "rejected"},
    "approved": {"sandbox-paid", "rejected"},
    "rejected": set(),
    "sandbox-paid": set(),
}


def firebase_app():
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={
            "projectId": os.getenv("FIREBASE_PROJECT_ID") or None
        })
    return firebase_admin.get_app()


def store():
    return firestore.client(
        app=firebase_app(), database_id=os.getenv("FIRESTORE_DATABASE_ID", "(default)")
    )


def principal(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Firebase ID token required")
    try:
        decoded = auth.verify_id_token(authorization[7:], app=firebase_app(), check_revoked=True)
        return decoded["uid"]
    except (ValueError, KeyError, firebase_admin.exceptions.FirebaseError) as exc:
        raise HTTPException(401, "Invalid or revoked Firebase ID token") from exc


def invoices(user):
    return store().collection("pazalink_users").document(user).collection("invoices")


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
    ref = invoices(user).document(identifier)
    data = {
        "id": identifier, "owner": user, "counterparty": payload.counterparty,
        "amount": str(payload.amount), "currency": payload.currency,
        "corridor": payload.corridor, "status": "draft", "created_at": stamp,
        "sandbox_only": True
    }
    batch = store().batch()
    batch.set(ref, data)
    batch.set(ref.collection("events").document(), {
        "kind": "created", "detail": "Created fictional sandbox invoice", "created_at": stamp
    })
    batch.commit()
    return {"id": identifier, "status": "draft", "sandbox_only": True}


@router.get("/invoices")
def list_invoices(user: str = Depends(principal)):
    rows = [doc.to_dict() for doc in invoices(user).limit(100).stream()]
    rows.sort(key=lambda row: row["created_at"], reverse=True)
    return {"items": rows, "sandbox_only": True}


@router.post("/invoices/{invoice_id}/transition")
def transition(invoice_id: str, payload: Transition, user: str = Depends(principal)):
    if not re.fullmatch(r"PL-[A-F0-9]{16}", invoice_id):
        raise HTTPException(404, "Invoice not found")
    ref = invoices(user).document(invoice_id)
    transaction = store().transaction()

    @firestore.transactional
    def update(txn):
        snapshot = ref.get(transaction=txn)
        if not snapshot.exists:
            raise HTTPException(404, "Invoice not found")
        current = snapshot.to_dict()["status"]
        if payload.status not in ALLOWED.get(current, set()):
            raise HTTPException(409, "Invalid sandbox state transition")
        txn.update(ref, {"status": payload.status})
        txn.set(ref.collection("events").document(), {
            "kind": "transition:" + payload.status,
            "detail": payload.reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    update(transaction)
    return {"id": invoice_id, "status": payload.status, "verified_payment": False}


@router.get("/invoices/{invoice_id}/events")
def invoice_events(invoice_id: str, user: str = Depends(principal)):
    if not re.fullmatch(r"PL-[A-F0-9]{16}", invoice_id):
        raise HTTPException(404, "Invoice not found")
    ref = invoices(user).document(invoice_id)
    if not ref.get().exists:
        raise HTTPException(404, "Invoice not found")
    data = [doc.to_dict() for doc in ref.collection("events").stream()]
    data.sort(key=lambda item: item["created_at"])
    return {"events": data}


@router.get("/integrations")
def integration_status(user: str = Depends(principal)):
    return {
        "owner": user, "paypal": "sandbox-adapter-in-app",
        "nebius": "optional-model-adapter-in-app",
        "africas_talking": "not-connected", "daraja_mpesa": "not-connected",
        "foreign_exchange": "not-connected", "escrow": "not-connected",
        "odoo": "not-connected", "production_settlement": False
    }
