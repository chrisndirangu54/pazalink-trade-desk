from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

from operations import router as operations_router, principal

app = FastAPI(title="PazaLink Trade Desk", version="0.3.0")
app.include_router(operations_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


class AnalyzeRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=80)
    amount: float = Field(gt=0, le=1_000_000)
    currency: str = Field(pattern="^[A-Z]{3}$")
    counterparty: str = Field(min_length=1, max_length=120)
    corridor: str = Field(min_length=1, max_length=80)
    note: str = Field(default="", max_length=1000)


class OrderRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=80)
    amount: str = Field(pattern=r"^\d+(\.\d{1,2})?$")
    description: str = Field(min_length=1, max_length=200)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "paypal_sandbox_configured": bool(os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET")),
        "sandbox_capture_enabled": os.getenv("ENABLE_SANDBOX_CAPTURE") == "true",
        "nebius_configured": bool(os.getenv("NEBIUS_API_KEY")),
        "nebius_model": os.getenv("NEBIUS_MODEL", "nvidia/nvidia-nemotron-3-nano-30b-a3b"),
    }


def rules_review(payload: AnalyzeRequest) -> dict[str, Any]:
    """Transparent fallback for interface testing; this is not generative AI."""
    note = payload.note.lower()
    flags = []
    if payload.amount >= 5000:
        flags.append("Large invoice: verify beneficiary and settlement instructions independently.")
    if "changed" in note or any(term in note for term in ("urgent", "new account", "override")):
        flags.append("Payment-instruction change language detected; confirm through a known contact channel.")
    if not flags:
        flags.append("No rule-based flag found. This does not verify the counterparty or payment.")
    return {
        "provider": "local-demo-rules",
        "summary": f"Review {payload.reference} for {payload.counterparty}: compare the invoice, amount, corridor and beneficiary details before settlement.",
        "checks": flags,
        "suggested_action": "Human review before any payment",
        "disclaimer": "Local demo rules only; no language model was called.",
    }


@app.post("/api/ai/analyze")
async def analyze(payload: AnalyzeRequest, user: str = Depends(principal)) -> dict[str, Any]:
    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        return rules_review(payload)

    base_url = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1").rstrip("/")
    model = os.getenv("NEBIUS_MODEL", "nvidia/nvidia-nemotron-3-nano-30b-a3b")
    body = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 450,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a cautious payment-operations assistant for small East African traders. "
                    "Return concise JSON with keys summary, checks (array), suggested_action. "
                    "Never claim to verify identity, payment, account ownership, fraud, or legal compliance. "
                    "Do not instruct the user to send money. Always recommend human verification of changed instructions."
                ),
            },
            {"role": "user", "content": payload.model_dump_json()},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        return {"provider": "nebius-token-factory", "model": model, "analysis": content}
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Nebius model request failed: {type(exc).__name__}") from exc


def paypal_sandbox_base_url() -> str:
    """Only PayPal's sandbox host is permitted, even when misconfigured."""
    value = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com").rstrip("/")
    if value != "https://api-m.sandbox.paypal.com":
        raise HTTPException(status_code=503, detail="Only the official PayPal sandbox API endpoint is permitted.")
    return value


async def paypal_access_token(client: httpx.AsyncClient) -> str:
    client_id = os.getenv("PAYPAL_CLIENT_ID")
    secret = os.getenv("PAYPAL_CLIENT_SECRET")
    if not client_id or not secret:
        raise HTTPException(status_code=503, detail="PayPal sandbox credentials are not configured on the server.")
    base = paypal_sandbox_base_url()
    response = await client.post(
        f"{base}/v1/oauth2/token",
        auth=(client_id, secret),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
    )
    if response.is_error:
        raise HTTPException(status_code=502, detail="PayPal sandbox authentication failed.")
    return response.json()["access_token"]


@app.post("/api/paypal/orders")
async def create_paypal_order(payload: OrderRequest, user: str = Depends(principal)) -> dict[str, Any]:
    if not os.getenv("PAYPAL_CLIENT_ID") or not os.getenv("PAYPAL_CLIENT_SECRET"):
        raise HTTPException(status_code=503, detail="PayPal sandbox credentials are not configured on the server.")
    base = paypal_sandbox_base_url()
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            token = await paypal_access_token(client)
            response = await client.post(
                f"{base}/v2/checkout/orders",
                headers={"Authorization": f"Bearer {token}", "PayPal-Request-Id": payload.reference},
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "reference_id": payload.reference,
                        "description": payload.description,
                        "amount": {"currency_code": "USD", "value": payload.amount},
                    }],
                    "application_context": {"brand_name": "PazaLink Trade Desk", "user_action": "PAY_NOW"},
                },
            )
            if response.is_error:
                raise HTTPException(status_code=502, detail="PayPal sandbox order creation failed.")
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach PayPal sandbox.") from exc


@app.post("/api/paypal/orders/{order_id}/capture")
async def capture_paypal_order(order_id: str, user: str = Depends(principal)) -> dict[str, Any]:
    if os.getenv("ENABLE_SANDBOX_CAPTURE") != "true":
        raise HTTPException(status_code=403, detail="Sandbox capture is disabled by default; enable only for controlled tests.")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,80}", order_id):
        raise HTTPException(status_code=422, detail="Invalid order ID.")
    raise HTTPException(status_code=501, detail="Capture requires order ownership, buyer approval and verified webhook integration; disabled.")
    # Previously available capture implementation removed from publicly reachable flow.
    if not os.getenv("PAYPAL_CLIENT_ID") or not os.getenv("PAYPAL_CLIENT_SECRET"):
        raise HTTPException(status_code=503, detail="PayPal sandbox credentials are not configured on the server.")
    base = paypal_sandbox_base_url()
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            token = await paypal_access_token(client)
            response = await client.post(
                f"{base}/v2/checkout/orders/{order_id}/capture",
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.is_error:
                raise HTTPException(status_code=502, detail="PayPal sandbox capture failed.")
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach PayPal sandbox.") from exc
