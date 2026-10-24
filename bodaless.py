"""Bodaless-inspired, tenant-scoped SIMULATION API.

All state is ephemeral in-memory test data, not a financial ledger. Never use for
real deposits, custody, FX quotes, KYC, lending, or cross-border settlement.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from operations import principal

router = APIRouter(prefix="/api/bodaless", tags=["bodaless-simulation"])
_lock = threading.RLock()
_records: dict[str, dict[str, dict]] = {}
COUNTRIES = {"KE": "KES", "UG": "UGX", "TZ": "TZS", "RW": "RWF"}
CHANNELS = ("app", "ussd", "sms", "voice", "whatsapp")
# Deliberately static FICTIONAL rates, never a live market price.
SAMPLE_RATES = {("KES", "UGX"): Decimal("27.50"), ("KES", "TZS"): Decimal("18.00"),
                ("KES", "RWF"): Decimal("10.00"), ("UGX", "KES"): Decimal("0.036"),
                ("TZS", "KES"): Decimal("0.055"), ("RWF", "KES"): Decimal("0.10")}


def now():
    return datetime.now(timezone.utc)


def pocket(user: str) -> dict[str, dict]:
    with _lock:
        return _records.setdefault(user, {})


def stored(user: str, identifier: str, kind: str):
    with _lock:
        item = pocket(user).get(identifier)
        if not item or item["kind"] != kind:
            raise HTTPException(404, "Demo record not found")
        return item


def new_record(user: str, kind: str, **fields):
    record_id = "BD-" + secrets.token_hex(10).upper()
    entry = {"id": record_id, "kind": kind, "sandbox_only": True,
             "created_at": now().isoformat(), **fields}
    with _lock:
        pocket(user)[record_id] = entry
    return entry


class QuoteRequest(BaseModel):
    source: Literal["KES", "UGX", "TZS", "RWF"]
    target: Literal["KES", "UGX", "TZS", "RWF"]
    amount: Decimal = Field(gt=0, le=1000000, max_digits=12, decimal_places=2)


def quote_values(source: str, target: str, amount: Decimal):
    if source == target:
        rate = Decimal("1")
    else:
        rate = SAMPLE_RATES.get((source, target))
    if rate is None:
        raise HTTPException(422, "Demo exchange pair unavailable; no live FX rate is provided")
    fee = (amount * Decimal("0.015")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    receive = ((amount - fee) * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"source": source, "target": target, "amount": str(amount),
            "illustrative_rate": str(rate), "illustrative_fee": str(fee),
            "illustrative_receive": str(receive), "rate_live": False,
            "rate_source": "fictional-static-fixture", "sandbox_only": True}


@router.post("/quotes")
def quote(payload: QuoteRequest, user: str = Depends(principal)):
    return quote_values(payload.source, payload.target, payload.amount)


class TransferRequest(BaseModel):
    source_country: Literal["KE", "UG", "TZ", "RW"]
    destination_country: Literal["KE", "UG", "TZ", "RW"]
    amount: Decimal = Field(gt=0, le=1000000, max_digits=12, decimal_places=2)
    recipient_phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    channel: Literal["app", "ussd", "sms", "voice", "whatsapp"]
    purpose: str = Field(min_length=2, max_length=160)


@router.post("/transfers", status_code=201)
def transfer(payload: TransferRequest, user: str = Depends(principal)):
    result = quote_values(COUNTRIES[payload.source_country],
                          COUNTRIES[payload.destination_country], payload.amount)
    return new_record(user, "transfer", state="awaiting-human-confirmation",
                      recipient_masked="***" + payload.recipient_phone[-4:],
                      source_country=payload.source_country,
                      destination_country=payload.destination_country,
                      channel=payload.channel, purpose=payload.purpose,
                      estimate=result, external_payment_id=None,
                      real_transfer_initiated=False)


class EscrowRequest(BaseModel):
    buyer_reference: str = Field(min_length=2, max_length=100)
    seller_reference: str = Field(min_length=2, max_length=100)
    item_description: str = Field(min_length=2, max_length=250)
    amount: Decimal = Field(gt=0, le=1000000, decimal_places=2)
    currency: Literal["KES", "UGX", "TZS", "RWF", "USD"]
    channel: Literal["app", "ussd", "sms", "voice", "whatsapp"]


@router.post("/escrows", status_code=201)
def escrow_create(payload: EscrowRequest, user: str = Depends(principal)):
    return new_record(user, "escrow", state="proposed", amount=str(payload.amount),
                      currency=payload.currency, item_description=payload.item_description,
                      buyer_reference=payload.buyer_reference,
                      seller_reference=payload.seller_reference, channel=payload.channel,
                      funded=False, funds_custodied=False, blockchain_tx=None,
                      history=[{"event": "proposed", "at": now().isoformat()}])


class EscrowAction(BaseModel):
    action: Literal["simulate-funding", "confirm-delivery", "open-dispute",
                    "simulate-release", "simulate-refund"]
    note: str = Field(default="", max_length=250)


ESCROW_MOVES = {"proposed": {"simulate-funding": "simulated-funded"},
                "simulated-funded": {"confirm-delivery": "delivery-confirmed",
                                     "open-dispute": "disputed"},
                "delivery-confirmed": {"simulate-release": "simulated-released",
                                       "open-dispute": "disputed"},
                "disputed": {"simulate-refund": "simulated-refunded"}}


@router.post("/escrows/{escrow_id}/actions")
def escrow_action(escrow_id: str, payload: EscrowAction, user: str = Depends(principal)):
    with _lock:
        item = stored(user, escrow_id, "escrow")
        next_state = ESCROW_MOVES.get(item["state"], {}).get(payload.action)
        if not next_state:
            raise HTTPException(409, "Invalid demo escrow transition")
        item["state"] = next_state
        item["funded"] = next_state in ("simulated-funded", "delivery-confirmed",
                                         "disputed", "simulated-released")
        item["history"].append({"event": payload.action, "note": payload.note,
                                "at": now().isoformat()})
        return item


class ListingRequest(BaseModel):
    side: Literal["buy", "sell"]
    category: Literal["cereals", "second-hand-clothes", "produce", "other"]
    description: str = Field(min_length=2, max_length=300)
    country: Literal["KE", "UG", "TZ", "RW"]
    price: Decimal = Field(gt=0, decimal_places=2)
    quantity: Decimal = Field(gt=0)
    unit: str = Field(min_length=1, max_length=30)
    channel: Literal["app", "ussd", "sms", "voice", "whatsapp"]


@router.post("/trade/listings", status_code=201)
def list_trade(payload: ListingRequest, user: str = Depends(principal)):
    return new_record(user, "listing", **payload.model_dump(mode="json"), state="open")


@router.get("/trade/listings")
def get_listings(user: str = Depends(principal)):
    with _lock:
        return {"items": [x for x in pocket(user).values() if x["kind"] == "listing"],
                "visibility": "owner-only-demo"}


@router.get("/records")
def get_records(user: str = Depends(principal)):
    with _lock:
        return {"items": list(pocket(user).values()), "ephemeral": True,
                "sandbox_only": True}


class VerificationRequest(BaseModel):
    channel: Literal["voice", "sms", "ussd", "app"]
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")


@router.post("/verification/challenges", status_code=201)
def challenge(payload: VerificationRequest, user: str = Depends(principal)):
    # Only validates demonstration code possession in this process, NOT identity.
    code = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_hex(12)
    proof = hashlib.sha256((salt + code).encode()).hexdigest()
    item = new_record(user, "challenge", state="pending", channel=payload.channel,
                      phone_masked="***" + payload.phone[-4:],
                      expires_at=(now() + timedelta(minutes=5)).isoformat(),
                      attempts=0, salt=salt, digest=proof)
    response = {k: v for k, v in item.items() if k not in ("salt", "digest")}
    # Development-only: never claim that an SMS or call has been placed.
    if os.getenv("BODALESS_SHOW_DEMO_OTP") == "true":
        response["demo_code"] = code
    response["delivered"] = False
    return response


class VerifyCode(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$")


@router.post("/verification/challenges/{challenge_id}/confirm")
def verify_code(challenge_id: str, payload: VerifyCode, user: str = Depends(principal)):
    with _lock:
        item = stored(user, challenge_id, "challenge")
        if item["state"] != "pending" or now() > datetime.fromisoformat(item["expires_at"]):
            raise HTTPException(409, "Challenge expired or completed")
        if item["attempts"] >= 5:
            raise HTTPException(429, "Too many demo attempts")
        item["attempts"] += 1
        digest = hashlib.sha256((item["salt"] + payload.code).encode()).hexdigest()
        if not secrets.compare_digest(digest, item["digest"]):
            raise HTTPException(422, "Incorrect demo code")
        item["state"] = "code-confirmed-demo"
        return {"code_confirmed": True, "identity_verified": False,
                "delivery_verified": False, "sandbox_only": True}


class RateLockRequest(QuoteRequest):
    hours: Literal[24] = 24


@router.post("/rate-locks", status_code=201)
def rate_lock(payload: RateLockRequest, user: str = Depends(principal)):
    estimate = quote_values(payload.source, payload.target, payload.amount)
    return new_record(user, "rate-lock", estimate=estimate,
                      expires_at=(now() + timedelta(hours=24)).isoformat(),
                      guaranteed=False, actual_fx_hedge=False)


class ChamaRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    country: Literal["KE", "UG", "TZ", "RW"]
    members: int = Field(ge=2, le=100)
    contribution: Decimal = Field(gt=0, decimal_places=2)


@router.post("/chamas", status_code=201)
def chama(payload: ChamaRequest, user: str = Depends(principal)):
    return new_record(user, "chama", **payload.model_dump(mode="json"),
                      pool_balance="0", real_wallet=False, bulk_payout_enabled=False)


class PassportRequest(BaseModel):
    merchant_alias: str = Field(min_length=2, max_length=80)
    country: Literal["KE", "UG", "TZ", "RW"]


@router.post("/trade-passports", status_code=201)
def passport(payload: PassportRequest, user: str = Depends(principal)):
    return new_record(user, "trade-passport", **payload.model_dump(),
                      kyc_verified=False, nft_minted=False, credit_eligible=False)


@router.get("/accounting/odoo-preview")
def accounting_export(user: str = Depends(principal)):
    with _lock:
        items = [r for r in pocket(user).values() if r["kind"] == "transfer"]
    return {"odoo_connected": False, "posted": False,
            "draft_entries": [{"reference": r["id"], "amount": r["estimate"]["amount"],
                               "currency": r["estimate"]["source"],
                               "journal_state": "unposted-sandbox-preview"} for r in items]}


class MessageRequest(BaseModel):
    text: str = Field(min_length=2, max_length=500)
    language: Literal["en", "sw"] = "en"
    channel: Literal["app", "ussd", "sms", "voice", "whatsapp"] = "app"


@router.post("/assistant")
def advisory(payload: MessageRequest, user: str = Depends(principal)):
    # Clearly labeled rules, never fabricated AI model inference or real credit score.
    lowered = payload.text.casefold()
    risk = any(word in lowered for word in ("urgent", "new account", "otp", "pin", "haraka"))
    response = ("Thibitisha maelekezo ya malipo moja kwa moja na mhusika."
                if payload.language == "sw" else
                "Independently verify beneficiary and payment instructions.") if risk else (
                "Bei na ada ni za majaribio; hakuna kiwango cha soko cha moja kwa moja."
                if payload.language == "sw" else
                "Rates and fees are illustrative. No live trade, FX or credit data is connected.")
    return {"provider": "local-rules-not-ai", "channel": payload.channel,
            "language": payload.language, "message": response,
            "trade_signal": None, "credit_score": None, "risk_flag": risk,
            "sandbox_only": True}


@router.get("/capabilities")
def capabilities():
    return {"mode": "simulation", "public_demo_ussd_code_active": False,
            "countries": COUNTRIES, "channels": list(CHANNELS),
            "integrations": {"africas_talking": "not-connected",
                             "payaza": "not-connected", "lisk": "not-connected",
                             "mpesa": "not-connected", "mtn_momo": "not-connected",
                             "airtel_money": "not-connected", "paypal": "separate-sandbox-adapter",
                             "visa_mastercard": "not-connected", "rtgs_swift": "not-connected",
                             "odoo": "preview-only"},
            "features": ["cross-border-quotes", "transfer-intents", "escrow-state-machine",
                         "trade-listings", "otp-simulation", "rate-lock-proposal",
                         "chama-proposal", "trade-passport-proposal",
                         "odoo-preview", "swahili-english-advice"],
            "no_real_funds_or_custody": True}
