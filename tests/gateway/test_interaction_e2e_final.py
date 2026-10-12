import pytest
from fastapi.testclient import TestClient
from src.main import app
import json
import jwt
from tests.gateway.test_risk_gate_end_to_end import access_token, insert_encounter_and_note

client = TestClient(app)

def test_interaction_blocks_sign(pg_conn, access_token):
    token, csrf = access_token
    
    meds = []
    stmts = [
        {"id": "stmt_1", "text": "dexmethylphenidate and tranylcypromine", "risk_tier": "red_flag", "statement_type": "medication_prescribed"}
    ]
    enc_id = insert_encounter_and_note(pg_conn, token, state="medication_review", meds=meds, stmts=stmts)
    
    # Check the safety flag
    stmt_res = client.get(f"/api/v1/encounters/{enc_id}", headers={"Authorization": f"Bearer {token}"})
    enc = stmt_res.json()
    stmt = next(s for s in enc["note"]["sections"]["assessment"]["statements"] if s["id"] == "stmt_1")
    print("\nINTERACTING PAIR STATEMENT:", json.dumps(stmt, indent=2))
    assert stmt["risk_tier"] == "red_flag"
    
    # Show it blocks /sign
    req_body_sign = {"edits": {}, "statement_determinations": {}}
    res_sign = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body_sign, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
    assert res_sign.status_code == 400
    print("\nSIGN BLOCKED RESPONSE:", res_sign.json())
    
    # 2. Safe pair
    stmts2 = [
        {"id": "stmt_2", "text": "ibuprofen and paracetamol", "risk_tier": "benign", "statement_type": "medication_prescribed"}
    ]
    enc_id2 = insert_encounter_and_note(pg_conn, token, state="medication_review", meds=[], stmts=stmts2)
    
    stmt_res2 = client.get(f"/api/v1/encounters/{enc_id2}", headers={"Authorization": f"Bearer {token}"})
    enc2 = stmt_res2.json()
    stmt2 = next(s for s in enc2["note"]["sections"]["assessment"]["statements"] if s["id"] == "stmt_2")
    print("\nSAFE PAIR STATEMENT:", json.dumps(stmt2, indent=2))
    assert stmt2["risk_tier"] == "benign"

from unittest.mock import patch
import httpx

def test_sign_503(pg_conn, access_token):
    token, csrf = access_token
    
    stmts = [
        {"id": "stmt_3", "text": "some diagnosis", "risk_tier": "requires_review", "statement_type": "inferred_diagnosis"}
    ]
    enc_id = insert_encounter_and_note(pg_conn, token, state="medication_review", meds=[], stmts=stmts)
    
    # Mock httpx.AsyncClient.post to raise RequestError
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = httpx.RequestError("Connection refused")
        
        req_body_sign = {"edits": {}, "statement_determinations": {"stmt_3": "some diagnosis"}}
        res_sign = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body_sign, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
        
        assert res_sign.status_code == 503
        assert "unreachable" in res_sign.json()["detail"]
