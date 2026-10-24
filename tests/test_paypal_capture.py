"""Offline order ownership and processor-state tests; no PayPal traffic."""
import copy
import json
import httpx
import pytest
from fastapi.testclient import TestClient
import app as module
from operations import principal

client = TestClient(module.app)
ORDER = "TESTORDER123"
PAYLOAD = {"reference": "PL-TEST", "amount": "12.40", "description": "Fictional invoice"}


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    module.app.dependency_overrides[principal] = lambda: "owner-a"
    for key, value in {"PAYPAL_CLIENT_ID":"test-client", "PAYPAL_CLIENT_SECRET":"test-secret",
                       "PAYPAL_ORDER_SIGNING_SECRET":"x" * 48, "ENABLE_SANDBOX_CAPTURE":"true"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("PAYPAL_BASE_URL", raising=False)
    yield
    module.app.dependency_overrides.clear()


def order(status="APPROVED"):
    result = {"id":ORDER, "intent":"CAPTURE", "status":status, "purchase_units":[{
        "reference_id":"PL-TEST", "amount":{"currency_code":"USD", "value":"12.40"}}]}
    if status == "COMPLETED":
        result["purchase_units"][0]["payments"] = {"captures":[{
            "id":"CAPTURE123", "status":"COMPLETED", "amount":{"currency_code":"USD", "value":"12.40"}}]}
    return result


def provider(monkeypatch, details=None, capture=None, capture_status=201):
    calls = []
    original = httpx.AsyncClient
    def handle(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token":"mock-token"})
        if request.method == "GET":
            return httpx.Response(200, json=details or order())
        if request.url.path.endswith("/capture"):
            return httpx.Response(capture_status, json=capture or order("COMPLETED"))
        result = order("CREATED")
        result["links"] = [{"rel":"approve", "href":"https://www.sandbox.paypal.com/checkoutnow?token="+ORDER}]
        return httpx.Response(201, json=result)
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    return calls


def receipt():
    return module.sign_order("owner-a", ORDER, module.OrderRequest(**PAYLOAD))


def capture(token=None):
    return client.post(f"/api/paypal/orders/{ORDER}/capture", json={"receipt":token or receipt()})


def test_creation_binds_owner_and_idempotency_to_request(monkeypatch):
    calls = provider(monkeypatch)
    first = client.post("/api/paypal/orders", json=PAYLOAD)
    assert first.status_code == 200
    data = first.json()
    assert data["sandbox_only"] is True
    assert data["approval_url"].startswith("https://www.sandbox.paypal.com/")
    assert module.verify_order(data["receipt"], "owner-a", ORDER)["amount"] == "12.40"
    client.post("/api/paypal/orders", json=PAYLOAD)
    creates = [r for r in calls if r.url.path.endswith("/orders")]
    assert creates[0].headers["PayPal-Request-Id"] == creates[1].headers["PayPal-Request-Id"]
    module.app.dependency_overrides[principal] = lambda: "owner-b"
    client.post("/api/paypal/orders", json=PAYLOAD)
    assert calls[-1].headers["PayPal-Request-Id"] != creates[0].headers["PayPal-Request-Id"]


def test_capture_requires_approved_matching_order(monkeypatch):
    calls = provider(monkeypatch)
    result = capture()
    assert result.status_code == 200
    assert result.json()["capture_id"] == "CAPTURE123"
    assert result.json()["production_payment"] is False
    assert [r.method for r in calls] == ["POST", "GET", "POST"]
    assert json.loads(calls[-1].content) == {}
    assert calls[-1].headers["Prefer"] == "return=representation"


@pytest.mark.parametrize("status", ["CREATED", "SAVED", "VOIDED", "PAYER_ACTION_REQUIRED"])
def test_unapproved_order_never_captured(monkeypatch, status):
    calls = provider(monkeypatch, details=order(status))
    assert capture().status_code == 409
    assert not any(r.url.path.endswith("/capture") for r in calls)


@pytest.mark.parametrize("case", ["owner", "tampered", "expired", "order"])
def test_invalid_ownership_receipt_never_calls_provider(monkeypatch, case):
    token = receipt()
    if case == "owner":
        module.app.dependency_overrides[principal] = lambda: "owner-b"
    elif case == "tampered":
        token += "0"
    elif case == "expired":
        monkeypatch.setattr(module.time, "time", lambda: 1)
        token = receipt()
        monkeypatch.setattr(module.time, "time", lambda: 10000)
    else:
        token = module.sign_order("owner-a", "OTHERORDER", module.OrderRequest(**PAYLOAD))
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kw: pytest.fail("Must reject before network"))
    assert capture(token).status_code == 403


@pytest.mark.parametrize("field,value", [("reference_id","OTHER"), ("currency_code","EUR"), ("value","12.41")])
def test_changed_order_is_rejected_before_capture(monkeypatch, field, value):
    details = order()
    unit = details["purchase_units"][0]
    (unit if field == "reference_id" else unit["amount"])[field] = value
    calls = provider(monkeypatch, details=details)
    assert capture().status_code == 502
    assert not any(r.url.path.endswith("/capture") for r in calls)


def test_completed_order_reconciles_without_second_capture(monkeypatch):
    calls = provider(monkeypatch, details=order("COMPLETED"))
    assert capture().json()["capture_id"] == "CAPTURE123"
    assert len(calls) == 2


@pytest.mark.parametrize("case", ["pending", "wrong_amount", "missing", "error"])
def test_capture_failure_or_mismatch_is_not_paid(monkeypatch, case):
    result = order("COMPLETED")
    transaction = result["purchase_units"][0]["payments"]["captures"][0]
    if case == "pending": transaction["status"] = "PENDING"
    if case == "wrong_amount": transaction["amount"]["value"] = "999"
    if case == "missing": result["purchase_units"][0].pop("payments")
    provider(monkeypatch, capture=result, capture_status=500 if case == "error" else 201)
    response = capture()
    assert response.status_code == 502
    assert "CAPTURE123" not in response.text


@pytest.mark.parametrize("amount", ["0", "0.00", "1000000.01"])
def test_order_amount_limits(amount):
    assert client.post("/api/paypal/orders", json={**PAYLOAD,"amount":amount}).status_code == 422


def test_creation_requires_signing_key_before_network(monkeypatch):
    monkeypatch.delenv("PAYPAL_ORDER_SIGNING_SECRET")
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kw: pytest.fail("No unsigned order"))
    assert client.post("/api/paypal/orders", json=PAYLOAD).status_code == 503
