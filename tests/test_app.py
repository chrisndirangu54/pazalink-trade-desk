"""Offline tests: no real PayPal or Nebius traffic is sent."""
import os
import pytest
from fastapi.testclient import TestClient

from app import app, AnalyzeRequest, rules_review
from operations import principal

client = TestClient(app)

@pytest.fixture(autouse=True)
def auth_override():
    app.dependency_overrides[principal] = lambda: "offline-test-user"
    yield
    app.dependency_overrides.clear()



def test_dashboard_and_health(monkeypatch):
    monkeypatch.delenv("PAYPAL_CLIENT_ID", raising=False)
    monkeypatch.delenv("PAYPAL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    assert client.get("/").status_code == 200
    result = client.get("/api/health")
    assert result.status_code == 200
    assert result.json()["paypal_sandbox_configured"] is False
    assert result.json()["nebius_configured"] is False


def test_local_rules_flag_changed_beneficiary(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    payload = {
        "reference": "PL-2048", "amount": 6000, "currency": "USD",
        "counterparty": "Example Trader", "corridor": "Nairobi-Kampala",
        "note": "URGENT: payment instructions changed to new account"
    }
    response = client.post("/api/ai/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "local-demo-rules"
    assert any("change" in c.lower() for c in body["checks"])
    assert "no language model" in body["disclaimer"].lower()


@pytest.mark.parametrize("field,value", [
    ("amount", 0), ("amount", -1), ("amount", 1000001),
    ("currency", "usd"), ("reference", "")
])
def test_bad_analysis_input_rejected(monkeypatch, field, value):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    payload = {
        "reference": "PL-1", "amount": 100, "currency": "USD",
        "counterparty": "Example", "corridor": "Nairobi-Kampala"
    }
    payload[field] = value
    assert client.post("/api/ai/analyze", json=payload).status_code == 422


def test_paypal_requires_server_side_credentials(monkeypatch):
    monkeypatch.delenv("PAYPAL_CLIENT_ID", raising=False)
    monkeypatch.delenv("PAYPAL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("PAYPAL_ORDER_SIGNING_SECRET", raising=False)
    request = {"reference":"PL-001", "amount":"12.40", "description":"Fictional invoice"}
    response = client.post("/api/paypal/orders", json=request)
    assert response.status_code == 503
    assert "sandbox" in response.json()["detail"].lower()
    monkeypatch.setenv("ENABLE_SANDBOX_CAPTURE", "true")
    response = client.post("/api/paypal/orders/FAKEORDER/capture", json={"receipt":"invalid"})
    assert response.status_code == 503


@pytest.mark.parametrize("amount", ["0.001", "-1.00", "1e5", "abc"])
def test_invalid_order_amount_rejected(amount):
    response = client.post("/api/paypal/orders", json={
        "reference":"PL-001", "amount":amount, "description":"Fictional invoice"
    })
    assert response.status_code == 422


def test_rules_do_not_claim_identity_verified():
    request = AnalyzeRequest(
        reference="PL-3", amount=100, currency="USD",
        counterparty="Example", corridor="Nairobi-Kampala"
    )
    outcome = rules_review(request)
    assert "human" in outcome["suggested_action"].lower()
    assert outcome["provider"] == "local-demo-rules"

def test_capture_opt_in_required(monkeypatch):
    monkeypatch.delenv("ENABLE_SANDBOX_CAPTURE", raising=False)
    result = client.post("/api/paypal/orders/FAKEORDER/capture", json={"receipt":"invalid"})
    assert result.status_code == 403


def test_reject_live_paypal_host(monkeypatch):
    from app import paypal_sandbox_base_url
    from fastapi import HTTPException
    monkeypatch.setenv("PAYPAL_BASE_URL", "https://api-m.paypal.com")
    with pytest.raises(HTTPException) as exc:
        paypal_sandbox_base_url()
    assert exc.value.status_code == 503

def test_endpoints_require_identity():
    app.dependency_overrides.clear()
    payload = {"reference":"PL-001","amount":100,"currency":"USD","counterparty":"Example","corridor":"Nairobi-Arusha"}
    assert client.post("/api/ai/analyze",json=payload).status_code == 401
    assert client.post("/api/paypal/orders",json={"reference":"X","amount":"5","description":"Test"}).status_code == 401
    assert client.post("/api/paypal/orders/ABC123/capture").status_code == 401
