import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
A = {"Authorization": "Bearer " + "a"*30}
B = {"Authorization": "Bearer " + "b"*30}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("PAZALINK_DB_PATH", str(tmp_path/"ops.sqlite3"))
    monkeypatch.setenv("PAZALINK_DEMO_TOKENS", "alice:" + "a"*30 + ",bob:" + "b"*30)


def test_auth_required():
    assert client.get("/api/ops/invoices").status_code == 401
    assert client.get("/api/ops/invoices", headers={"Authorization":"Bearer wrong"}).status_code == 401


def test_invoice_isolation_and_audit():
    created = client.post("/api/ops/invoices", headers=A, json={
        "counterparty":"Demo merchant", "amount":"42.50",
        "currency":"USD", "corridor":"Nairobi-Arusha"
    })
    assert created.status_code == 201, created.text
    invoice = created.json()["id"]
    assert len(client.get("/api/ops/invoices", headers=A).json()["items"]) == 1
    assert client.get("/api/ops/invoices", headers=B).json()["items"] == []
    assert client.get(f"/api/ops/invoices/{invoice}/events", headers=B).status_code == 404
    assert client.post(f"/api/ops/invoices/{invoice}/transition",
                       headers=B, json={"status":"review", "reason":"Check data"}).status_code == 404
    assert client.post(f"/api/ops/invoices/{invoice}/transition",
                       headers=A, json={"status":"sandbox-paid", "reason":"No proof"}).status_code == 409
    for state in ("review", "approved", "sandbox-paid"):
        result = client.post(f"/api/ops/invoices/{invoice}/transition",
                             headers=A, json={"status":state, "reason":"Controlled demo"})
        assert result.status_code == 200, result.text
        assert result.json()["verified_payment"] is False
    events = client.get(f"/api/ops/invoices/{invoice}/events", headers=A).json()["events"]
    assert len(events) == 4
    assert client.post(f"/api/ops/invoices/{invoice}/transition",
                       headers=A, json={"status":"review","reason":"Again"}).status_code == 409


def test_invalid_invoice_and_integration_honesty():
    bad = client.post("/api/ops/invoices", headers=A, json={
        "counterparty":"x", "amount":"-1", "currency":"usd", "corridor":"a"
    })
    assert bad.status_code == 422
    integrations = client.get("/api/ops/integrations", headers=A).json()
    assert integrations["production_settlement"] is False
    assert integrations["daraja_mpesa"] == "not-connected"
