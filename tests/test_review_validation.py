"""Provider-adapter contract tests using mocked HTTP, never real model inference."""
import json
import httpx
import pytest
from fastapi.testclient import TestClient
import app as module
from operations import principal

PAYLOAD={"reference":"TEST-001","amount":6000,"currency":"USD","counterparty":"Fictional trader","corridor":"Nairobi-Kampala","note":"Urgent: changed beneficiary"}
client=TestClient(module.app)

@pytest.fixture(autouse=True)
def identity(monkeypatch):
    module.app.dependency_overrides[principal]=lambda:'test-user'
    monkeypatch.setenv('NEBIUS_API_KEY','offline-test-secret')
    monkeypatch.delenv('NEBIUS_BASE_URL',raising=False)
    monkeypatch.delenv('NEBIUS_MODEL',raising=False)
    yield
    module.app.dependency_overrides.clear()

def mock_provider(monkeypatch, content, finish='stop', status=200):
    original=httpx.AsyncClient
    sent=[]
    def handle(request):
        sent.append(request)
        return httpx.Response(status,json={"id":"mock-request-1","choices":[{"finish_reason":finish,"message":{"content":content}}]})
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handle),**kwargs))
    return sent

def test_valid_model_response_is_structured_and_never_authorizes_payment(monkeypatch):
    sent=mock_provider(monkeypatch,json.dumps({"summary":"Check invoice and beneficiary.","checks":["Confirm changed instructions independently."],"suggested_action":"Send money now"}))
    response=client.post('/api/ai/analyze',json=PAYLOAD)
    assert response.status_code==200
    data=response.json()
    assert data['provider']=='nebius-token-factory'
    assert data['suggested_action']=='Human review before any payment'
    assert data['payment_authorized'] is False
    assert data['request_id']=='mock-request-1'
    request=sent[0]
    assert str(request.url)=='https://api.tokenfactory.nebius.com/v1/chat/completions'
    assert json.loads(request.content)['model']=='nvidia/Nemotron-3_5-Lightning'
    assert 'offline-test-secret' not in response.text

@pytest.mark.parametrize('content,finish',[
    ('not json','stop'),
    ('{"summary":"short"}','stop'),
    (json.dumps({"summary":"check","checks":["verify"],"suggested_action":"review","verified":True}),'stop'),
    (json.dumps({"summary":"check","checks":[""],"suggested_action":"review"}),'stop'),
    (json.dumps({"summary":"check","checks":["verify"],"suggested_action":"review"}),'length'),
])
def test_malformed_or_truncated_model_output_fails_without_rules_fallback(monkeypatch,content,finish):
    mock_provider(monkeypatch,content,finish)
    response=client.post('/api/ai/analyze',json=PAYLOAD)
    assert response.status_code==502
    assert 'local-demo-rules' not in response.text

def test_provider_failure_is_not_disguised_as_success(monkeypatch):
    mock_provider(monkeypatch,'',status=429)
    assert client.post('/api/ai/analyze',json=PAYLOAD).status_code==502

def test_unapproved_provider_host_never_receives_a_key(monkeypatch):
    monkeypatch.setenv('NEBIUS_BASE_URL','https://example.invalid/v1')
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kwargs:pytest.fail('Network must not be attempted'))
    assert client.post('/api/ai/analyze',json=PAYLOAD).status_code==503

def test_rules_demo_is_opt_in_and_loopback_only(monkeypatch):
    monkeypatch.delenv('ENABLE_LOCAL_RULES_DEMO',raising=False)
    local=TestClient(module.app,base_url='http://localhost',client=('127.0.0.1',12345))
    assert local.post('/api/demo/analyze',json=PAYLOAD).status_code==404
    monkeypatch.setenv('ENABLE_LOCAL_RULES_DEMO','true')
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kwargs:pytest.fail('Demo must never invoke a provider'))
    result=local.post('/api/demo/analyze',json=PAYLOAD)
    assert result.status_code==200
    assert result.json()['provider']=='local-demo-rules'
    assert result.json()['payment_authorized'] is False
    assert local.post('/api/demo/analyze',json=PAYLOAD,headers={'Origin':'https://evil.example'}).status_code==403
    remote=TestClient(module.app,base_url='https://example.com',client=('203.0.113.1',12345))
    assert remote.post('/api/demo/analyze',json=PAYLOAD).status_code==403

def test_demo_does_not_unlock_protected_endpoints(monkeypatch):
    monkeypatch.setenv('ENABLE_LOCAL_RULES_DEMO','true')
    module.app.dependency_overrides.clear()
    assert client.post('/api/ai/analyze',json=PAYLOAD).status_code==401
    assert client.get('/api/ops/invoices').status_code==401
