"""Firebase backend tests; no real Firebase credentials or network required."""
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import app
import operations

client = TestClient(app)

@pytest.fixture(autouse=True)
def mocked_firebase(monkeypatch):
    monkeypatch.setattr(operations, "firebase_app", lambda: object())
    def fake_verify(token, **kwargs):
        if token == "alice-token":
            return {"uid": "alice"}
        if token == "bob-token":
            return {"uid": "bob"}
        raise ValueError("bad token")
    monkeypatch.setattr(operations.auth, "verify_id_token", fake_verify)

def test_auth_enforced():
    assert client.get("/api/ops/invoices").status_code == 401
    assert client.get("/api/ops/invoices", headers={"Authorization":"Bearer wrong"}).status_code == 401

def test_firebase_uid_is_verified():
    assert operations.principal("Bearer alice-token") == "alice"
    assert operations.principal("Bearer bob-token") == "bob"
    with pytest.raises(HTTPException) as exc:
        operations.principal("Bearer forged")
    assert exc.value.status_code == 401

def test_tenant_paths(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(operations, "store", lambda: db)
    operations.invoices("alice")
    db.collection.assert_called_with("pazalink_users")
    db.collection.return_value.document.assert_called_with("alice")
    operations.invoices("bob")
    db.collection.return_value.document.assert_called_with("bob")

def test_validation_and_integration_status():
    token = {"Authorization":"Bearer alice-token"}
    result = client.post("/api/ops/invoices", headers=token, json={
        "counterparty":"Example", "amount":"-1", "currency":"usd", "corridor":"EAC"})
    assert result.status_code == 422
    response = client.get("/api/ops/integrations",headers=token)
    assert response.status_code == 200
    assert response.json()["production_settlement"] is False

def test_missing_or_invalid_invoice_id():
    token = {"Authorization":"Bearer alice-token"}
    response = client.get("/api/ops/invoices/not-valid/events", headers=token)
    assert response.status_code == 404
    response = client.post("/api/ops/invoices/not-valid/transition",headers=token,
                           json={"status":"review","reason":"check transaction"})
    assert response.status_code == 404

def test_state_machine():
    assert operations.ALLOWED["draft"] == {"review"}
    assert "sandbox-paid" not in operations.ALLOWED["draft"]
    assert operations.ALLOWED["sandbox-paid"] == set()
