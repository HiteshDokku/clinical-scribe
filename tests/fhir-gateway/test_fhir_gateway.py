import pytest
import pytest_asyncio
import uuid
import json
import base64
import sys
import httpx
from fastapi.testclient import TestClient

from src.main import app as fhir_gateway_app
from src.main import PushRequest

client = TestClient(fhir_gateway_app)

# Helper mock response
class MockResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
    def json(self):
        return self._json
    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("Error", request=httpx.Request("GET", "url"), response=self)

@pytest.fixture
def mock_gateway_responses(monkeypatch):
    """Mocks fhir-gateway's outgoing calls to the main gateway."""
    responses = {}
    
    # We will mock httpx.AsyncClient.get
    async def mock_get(self, url, *args, **kwargs):
        if url in responses:
            return responses[url]
        return MockResponse(404, {"detail": "Not found"})
        
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
    return responses

@pytest.fixture
def mock_fhir_push(monkeypatch):
    """Mocks execute_fhir_push so it doesn't hit the real FHIR server."""
    payloads = []

    async def mock_execute(target_url, bundle_dict):
        payloads.append((target_url, bundle_dict))
        return {"status": "ok"}

    monkeypatch.setattr("src.main.execute_fhir_push", mock_execute)
    return payloads

def test_egress_allowlist_refusal(mock_gateway_responses):
    enc_id = str(uuid.uuid4())
    mock_gateway_responses[f"http://gateway:8000/api/v1/encounters/{enc_id}"] = MockResponse(
        200, {"id": enc_id, "state": "signed", "patient_ref": "pat123"}
    )
    mock_gateway_responses[f"http://gateway:8000/api/v1/encounters/{enc_id}/note"] = MockResponse(
        200, {"note_text": "Sample note", "sections": {"assessment": {"statements": []}}}
    )

    res = client.post("/push", json={
        "encounter_id": enc_id,
        "target_url": "http://evil.com/fhir"
    })
    
    assert res.status_code == 403
    assert "Egress restricted" in res.text

def test_unsigned_note_rejection(mock_gateway_responses):
    enc_id = str(uuid.uuid4())
    mock_gateway_responses[f"http://gateway:8000/api/v1/encounters/{enc_id}"] = MockResponse(
        200, {"id": enc_id, "state": "draft", "patient_ref": "pat123"}
    )

    res = client.post("/push", json={
        "encounter_id": enc_id
    })
    
    assert res.status_code == 400
    assert "Cannot push unsigned note" in res.text

def test_audio_transcript_absence_from_payload(mock_gateway_responses, mock_fhir_push):
    enc_id = str(uuid.uuid4())
    mock_gateway_responses[f"http://gateway:8000/api/v1/encounters/{enc_id}"] = MockResponse(
        200, {"id": enc_id, "state": "signed", "patient_ref": "pat123"}
    )
    mock_gateway_responses[f"http://gateway:8000/api/v1/encounters/{enc_id}/note"] = MockResponse(
        200, {"note_text": "Sample note", "sections": {"assessment": {"statements": []}}}
    )

    res = client.post("/push", json={
        "encounter_id": enc_id
    })
    
    assert res.status_code == 200
    assert len(mock_fhir_push) == 1
    
    target_url, bundle_dict = mock_fhir_push[0]
    bundle_str = json.dumps(bundle_dict).lower()
    
    # Verify no audio or transcript is present
    assert "audio" not in bundle_str
    assert "transcript" not in bundle_str
    assert "segments" not in bundle_str
    
    # Verify idempotency key behavior implicitly
    assert bundle_dict["resourceType"] == "Bundle"


@pytest.mark.asyncio
async def test_idempotency_key_reuse(monkeypatch):
    """
    Test that execute_fhir_push reuses the exact same Bundle ID 
    as the Idempotency-Key if retries occur.
    """
    idempotency_keys = []
    
    async def mock_post(self, url, *args, **kwargs):
        headers = kwargs.get("headers", {})
        if "Idempotency-Key" in headers:
            idempotency_keys.append(headers["Idempotency-Key"])
        if len(idempotency_keys) < 2:
            raise httpx.RequestError("Simulated network failure on first try", request=httpx.Request("POST", url))
        return MockResponse(200, {"status": "ok"})
        
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    
    from src.main import execute_fhir_push, FHIR_ALLOWLIST_HOST, FHIR_ALLOWLIST_PORT
    bundle_dict = {"id": "test-bundle-123"}
    scheme = "https" if str(FHIR_ALLOWLIST_PORT) == "8443" else "http"
    target_url = f"{scheme}://{FHIR_ALLOWLIST_HOST}:{FHIR_ALLOWLIST_PORT}/fhir"
    
    result = await execute_fhir_push(target_url, bundle_dict)
    
    assert result == {"status": "ok"}
    assert len(idempotency_keys) == 2
    # Ensure idempotency key is the same across retries
    assert idempotency_keys[0] == idempotency_keys[1]
    assert idempotency_keys[0] == "test-bundle-123"
