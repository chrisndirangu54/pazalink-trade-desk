"""Offline Bodaless test coverage: no external rails invoked."""
from fastapi.testclient import TestClient
from app import app
from operations import principal

client = TestClient(app)

def setup_function():
    app.dependency_overrides[principal] = lambda: "bodaless-test-tenant"

def teardown_function():
    app.dependency_overrides.clear()

def test_capabilities_and_quote():
    cap = client.get("/api/bodaless/capabilities").json()
    assert cap["no_real_funds_or_custody"]
    assert cap["integrations"]["payaza"] == "not-connected"
    q = client.post("/api/bodaless/quotes", json={"source":"KES","target":"UGX","amount":"100"}).json()
    assert q["rate_live"] is False
    assert q["illustrative_receive"] == "2708.75"

def test_quote_rejects_unconfigured_corridor():
    r = client.post("/api/bodaless/quotes", json={"source":"RWF","target":"TZS","amount":"100"})
    assert r.status_code == 422

def test_transfer_creates_intent_not_payment():
    r = client.post("/api/bodaless/transfers", json={
        "source_country":"KE", "destination_country":"UG", "amount":"100",
        "recipient_phone":"+256771234567", "channel":"ussd", "purpose":"Cereal order"})
    assert r.status_code == 201
    assert r.json()["real_transfer_initiated"] is False
    assert r.json()["recipient_masked"] == "***4567"

def test_escrow_state_machine_and_no_custody():
    r = client.post("/api/bodaless/escrows",json={
        "buyer_reference":"buyer", "seller_reference":"seller",
        "item_description":"Maize delivery", "amount":"1000", "currency":"KES", "channel":"voice"})
    assert r.status_code == 201
    item = r.json()
    assert item["funds_custodied"] is False
    url = "/api/bodaless/escrows/" + item["id"] + "/actions"
    assert client.post(url,json={"action":"simulate-release"}).status_code == 409
    for action,state in [("simulate-funding","simulated-funded"),
                         ("confirm-delivery","delivery-confirmed"),
                         ("simulate-release","simulated-released")]:
        done=client.post(url,json={"action":action})
        assert done.status_code == 200
        assert done.json()["state"] == state
        assert done.json()["funds_custodied"] is False

def test_listing_chama_passport_and_accounting():
    listing = client.post("/api/bodaless/trade/listings",json={
        "side":"sell","category":"cereals","description":"Maize",
        "country":"KE","price":"900","quantity":"2","unit":"bag","channel":"sms"})
    assert listing.status_code == 201
    assert len(client.get("/api/bodaless/trade/listings").json()["items"]) >= 1
    chama = client.post("/api/bodaless/chamas",json={
        "name":"Demo Chama","country":"KE","members":10,"contribution":"100"}).json()
    assert chama["bulk_payout_enabled"] is False
    passport = client.post("/api/bodaless/trade-passports",json={
        "merchant_alias":"Demo Trader","country":"KE"}).json()
    assert passport["kyc_verified"] is False
    assert client.get("/api/bodaless/accounting/odoo-preview").json()["posted"] is False

def test_assistant_is_rules_not_model():
    r=client.post("/api/bodaless/assistant",json={
        "text":"haraka send to new account", "language":"sw", "channel":"voice"}).json()
    assert r["provider"] == "local-rules-not-ai"
    assert r["risk_flag"] is True
    assert r["credit_score"] is None

def test_auth_required():
    app.dependency_overrides.clear()
    assert client.get("/api/bodaless/records").status_code == 401
    assert client.post("/api/bodaless/transfers",json={}).status_code == 401
