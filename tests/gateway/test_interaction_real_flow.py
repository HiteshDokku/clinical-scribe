import pytest
from fastapi.testclient import TestClient
from src.main import app
import json
import jwt
from unittest.mock import patch
from tests.gateway.test_risk_gate_end_to_end import access_token, insert_encounter_and_note
import httpx
import uuid
from fastapi.testclient import TestClient
from src.main import app
client = TestClient(app)

class MockLLMResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
    def json(self):
        return self.json_data
    def raise_for_status(self):
        pass

def test_interaction_real_flow(pg_conn, access_token):
    token, csrf = access_token
    
    print("\n--- SAFETY SERVICE IS REAL (calls to http://safety:8002 are unmocked) ---")
    print("--- LLM SERVICE IS MOCKED (calls to http://llm:8080 are mocked) ---")
    
    # Pair from the table: sparfloxacin and erythromycin
    enc_id = insert_encounter_and_note(pg_conn, token, state="diagnosis_review", meds=[], stmts=[])

    llm_prescribe_output = {
        "sections": {"plan": {"statements": []}},
        "medications": [
            {"id": "m1", "verbatim": "sparfloxacin"},
            {"id": "m2", "verbatim": "erythromycin"}
        ]
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        async def side_effect(*args, **kwargs):
            url = kwargs.get("url")
            if not url and len(args) > 1:
                url = args[1]
            elif not url and len(args) == 1:
                url = args[0]
            
            if isinstance(url, str) and "llm:8080" in url:
                return MockLLMResponse(llm_prescribe_output)
            
            # Bypass the mock on .post by calling .request directly
            kwargs.pop("url", None)
            async with httpx.AsyncClient() as temp_client:
                return await temp_client.request("POST", url, **kwargs)
            
        mock_post.side_effect = side_effect
        
        # 1. Prescribe
        res_prescribe = client.post(f"/api/v1/encounters/{enc_id}/confirm-diagnosis", json={"confirmed_diagnosis": "Test"}, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
        print("PRESCRIBE RES:", res_prescribe.json())
        assert res_prescribe.status_code == 200
        
        # Check safety flags in the note
        stmt_res = client.get(f"/api/v1/encounters/{enc_id}", headers={"Authorization": f"Bearer {token}"})
        note = stmt_res.json()["note"]
        print("\nNOTE SAFETY FLAGS:", json.dumps(note.get("safety_flags", []), indent=2))
        assert len(note.get("safety_flags", [])) > 0
        
        # 2. Sign (blocked because unacknowledged interaction flag)
        req_body_sign = {
            "edits": {},
            "statement_determinations": {},
            "medication_entries": {"m1": "sparfloxacin 200mg po daily", "m2": "erythromycin 500mg po qid"},
            "acknowledged_flags": []
        }
        res_sign = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body_sign, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
        print("\nSIGN BLOCKED (UNACKNOWLEDGED INTERACTION) RESPONSE:", res_sign.json())
        assert res_sign.status_code == 400
        assert "unacknowledged interaction" in res_sign.json()["detail"]
        
        # Now acknowledge the interaction flag and sign succeeds
        flag_ref = note["safety_flags"][0]["source_ref"]
        req_body_sign_ack = {
            "edits": {},
            "statement_determinations": {},
            "medication_entries": {"m1": "sparfloxacin 200mg po daily", "m2": "erythromycin 500mg po qid"},
            "acknowledged_flags": [flag_ref]
        }
        res_sign_ack = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body_sign_ack, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
        print("\nSIGN AFTER ACKNOWLEDGING INTERACTION RESPONSE:", res_sign_ack.json() if res_sign_ack.status_code != 200 else "SUCCESS")
        assert res_sign_ack.status_code == 200
        
        # 3. Pair NOT in table: ibuprofen and paracetamol
        llm_prescribe_output["medications"] = [
            {"id": "m1", "verbatim": "ibuprofen"},
            {"id": "m2", "verbatim": "paracetamol"}
        ]
        enc_id2 = insert_encounter_and_note(pg_conn, token, state="diagnosis_review", meds=[], stmts=[])
            
        res_prescribe2 = client.post(f"/api/v1/encounters/{enc_id2}/confirm-diagnosis", json={"confirmed_diagnosis": "Test"}, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
        assert res_prescribe2.status_code == 200
        
        stmt_res2 = client.get(f"/api/v1/encounters/{enc_id2}", headers={"Authorization": f"Bearer {token}"})
        note2 = stmt_res2.json()["note"]
        print("\nSAFE PAIR SAFETY FLAGS:", json.dumps(note2.get("safety_flags", []), indent=2))
        assert len(note2.get("safety_flags", [])) == 0
        
        req_body_sign2 = {"edits": {}, "statement_determinations": {}, "medication_entries": {"m1": "ibuprofen oral 400mg", "m2": "paracetamol 500mg tab"}, "acknowledged_flags": []}
        res_sign2 = client.post(f"/api/v1/encounters/{enc_id2}/sign", json=req_body_sign2, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
        print("\nSIGN SAFE PAIR (NO FLAGS) RESPONSE:", res_sign2.json() if res_sign2.status_code != 200 else "SUCCESS")
        assert res_sign2.status_code == 200
        
        # 4. Both UNRESOLVED but in table
        llm_prescribe_output["medications"] = [
            {"id": "m1", "verbatim": "amiodarone 650 mg tablet"},
            {"id": "m2", "verbatim": "escitalopram 10mg"}
        ]
        enc_id3 = insert_encounter_and_note(pg_conn, token, state="diagnosis_review", meds=[], stmts=[])
            
        res_prescribe3 = client.post(f"/api/v1/encounters/{enc_id3}/confirm-diagnosis", json={"confirmed_diagnosis": "Test"}, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
        assert res_prescribe3.status_code == 200
        
        stmt_res3 = client.get(f"/api/v1/encounters/{enc_id3}", headers={"Authorization": f"Bearer {token}"})
        note3 = stmt_res3.json()["note"]
        print("\nUNRESOLVED PAIR SAFETY FLAGS:", json.dumps(note3.get("safety_flags", []), indent=2))
        assert len(note3.get("safety_flags", [])) > 0
        
        # Attempting to sign without acknowledging flag is blocked
        req_body_sign3 = {
            "edits": {},
            "statement_determinations": {},
            "medication_entries": {"m1": "amiodarone 200mg po daily", "m2": "escitalopram 10mg po daily"},
            "acknowledged_flags": []
        }
        res_sign3 = client.post(f"/api/v1/encounters/{enc_id3}/sign", json=req_body_sign3, headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}, cookies={"csrf_token": csrf})
        print("\nSIGN UNRESOLVED PAIR BLOCKED RESPONSE:", res_sign3.json())
        assert res_sign3.status_code == 400
        assert "unacknowledged interaction" in res_sign3.json()["detail"]

