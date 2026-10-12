import pytest
from fastapi.testclient import TestClient
from src.main import app
import json
import uuid
import psycopg
from datetime import datetime, timezone

from tests.gateway.test_risk_gate_end_to_end import access_token, insert_encounter_and_note

@pytest.fixture
def client():
    return TestClient(app)

def test_edit_assessment_pulmonary_embolism(client, pg_conn, access_token):
    token, csrf = access_token
    
    # Create encounter with a drafted assessment statement
    stmts = [{"id": "s1", "text": "Chest pain", "evidence": [{"id": "1", "text": "chest pain", "start": 0, "end": 10}], "risk_tier": "common"}]
    enc_id = insert_encounter_and_note(pg_conn, token, state="medication_review", meds=[], stmts=stmts)
    
    # Attempt to sign with edited statement
    res = client.post(
        f"/api/v1/encounters/{enc_id}/sign",
        json={
            "statement_determinations": {"s1": "Pulmonary embolism"},
            "medication_entries": {},
            "acknowledged_flags": []
        },
        headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf},
        cookies={"csrf_token": csrf}
    )
    
    print("SIGN BLOCKED RESPONSE:", res.json())
    assert res.status_code == 400
    assert "unresolved high risk" in res.json().get("detail", "").lower()

def test_benign_tier_blocks_sign(client, pg_conn, access_token, monkeypatch):
    token, csrf = access_token
    
    # Create encounter with a drafted assessment statement
    stmts = [{"id": "s2", "text": "Mild headache", "risk_tier": "benign"}]
    enc_id = insert_encounter_and_note(pg_conn, token, state="medication_review", meds=[], stmts=stmts)
    
    # Mock safety service to return "benign"
    class MockSafetyResp:
        status_code = 200
        def json(self):
            return {"risk_tier": "benign"}
            
    async def mock_post(*args, **kwargs):
        return MockSafetyResp()
        
    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    # Attempt to sign
    res = client.post(
        f"/api/v1/encounters/{enc_id}/sign",
        json={
            "statement_determinations": {},
            "medication_entries": {},
            "acknowledged_flags": []
        },
        headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf},
        cookies={"csrf_token": csrf}
    )
    
    print("BENIGN TIER SIGN BLOCKED RESPONSE:", res.json())
    assert res.status_code == 400
    assert "unresolved high risk" in res.json().get("detail", "").lower()

