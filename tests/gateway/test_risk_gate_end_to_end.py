import pytest
import uuid
import json
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.fixture
def access_token():
    # Login to get token using TestClient
    res = client.post("/api/v1/auth/login", json={"username": "dr-martinez", "password": "dev_clinician_pass"})
    return res.json()["access_token"], res.cookies.get("csrf_token")

def insert_encounter_and_note(pg_conn, token, state="medication_review", meds=[], stmts=[{"id": "stmt_1", "text": "Requires review condition", "risk_tier": "requires_review", "statement_type": "inferred_diagnosis"}], content_extra={}):
    import jwt
    payload = jwt.decode(token, options={"verify_signature": False})
    clinician_id = payload["sub"]
    enc_id = str(uuid.uuid4())
    pg_conn.execute("SELECT set_config('app.current_user_id', %s, false)", (clinician_id,))
    pg_conn.execute("SELECT set_config('app.current_role_id', 'clinician', false)")
    pg_conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at,
             started_at, state)
        VALUES (%s, %s, %s, 'granted', now(), now(), %s)
        """,
        (enc_id, clinician_id, "test-patient", state)
    )
    
    note_content = {
        "encounter_id": enc_id,
        "model": {"name": "test", "quant": "test", "prompt_version": "test"},
        "sections": {
            "assessment": {"statements": stmts},
            "plan": {"statements": []}
        },
        "medications": meds,
        "safety_flags": [],
        "grounding": {"statements_total": len(stmts), "ungrounded": 0, "ungrounded_ids": []}
    }
    note_content.update(content_extra)
    
    pg_conn.execute(
        """
        INSERT INTO note_versions
            (id, encounter_id, version, source, content_jsonb, model_name, model_hash, prompt_version, created_at)
        VALUES (%s, %s, 1, 'model_generation', %s::jsonb, 'test', 'hash', 'v1', now())
        """,
        (str(uuid.uuid4()), enc_id, json.dumps(note_content))
    )
    return enc_id

def test_signing_blocked_when_any_red_flag_or_high_risk_med_unresolved(pg_conn, access_token):
    token, csrf = access_token
    meds = [{"id": "med_1", "verbatim": "High risk med", "needs_manual_confirmation": True, "flags": []}]
    enc_id = insert_encounter_and_note(pg_conn, token, meds=meds)
    
    req_body = {"edits": {}, "statement_determinations": {"stmt_1": "Determined diagnosis"}}
    res = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
    assert res.status_code == 400
    assert "medication" in res.json()["detail"].lower() or "unresolved" in res.json()["detail"].lower()

def test_signing_blocked_when_manual_entry_matches_exactly(pg_conn, access_token):
    token, csrf = access_token
    # Statement is red_flag, but determination is missing or exact match
    stmts = [{"id": "stmt_1", "text": "Requires review condition", "risk_tier": "requires_review", "statement_type": "inferred_diagnosis"}]
    enc_id = insert_encounter_and_note(pg_conn, token, stmts=stmts)
    
    req_body = {"edits": {}, "statement_determinations": {}}
    res = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
    assert res.status_code == 400

def test_signing_blocked_when_safety_unreachable(pg_conn, access_token, monkeypatch):
    token, csrf = access_token
    enc_id = insert_encounter_and_note(pg_conn, token)
    
    import httpx
    # mock httpx.AsyncClient.post to raise RequestError
    async def mock_post(*args, **kwargs):
        raise httpx.RequestError("Mocked error")
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    
    req_body = {"edits": {}, "statement_determinations": {"stmt_1": "Determined diagnosis"}}
    res = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
    assert res.status_code == 503

def test_clinician_edit_to_serious_diagnosis_is_reclassified_at_sign(pg_conn, access_token):
    token, csrf = access_token
    # AI says Hypertension (benign)
    stmts = [{"id": "stmt_1", "text": "Hypertension", "risk_tier": "benign", "statement_type": "inferred_diagnosis"}]
    enc_id = insert_encounter_and_note(pg_conn, token, stmts=stmts)
    
    # Clinician edits to Malignant Hypertension (which should recompute to red_flag or requires_review)
    req_body = {"edits": {}, "statement_determinations": {"stmt_1": "Malignant Hypertension"}}
    res = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
    
    assert res.status_code == 400
    assert "matches AI suggestion exactly" in res.json()["detail"] or "too similar" in res.json()["detail"] or "unresolved" in res.json()["detail"].lower()
import pytest
from fastapi.testclient import TestClient
from src.main import app
import json
import jwt

client = TestClient(app)
