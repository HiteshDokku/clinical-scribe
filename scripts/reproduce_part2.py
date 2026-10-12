import os
import uuid
import json
import psycopg
from difflib import SequenceMatcher
import re
from fastapi.testclient import TestClient

from src.main import app

def is_too_similar_current(manual: str, ai_text: str) -> bool:
    if len(manual.strip()) < 10:
        return True # Too short to be a meaningful manual override
    def norm(s):
        return re.sub(r'[^\w\s]', '', s.lower().strip())
    norm_man = norm(manual)
    norm_ai = norm(ai_text)
    if not norm_man or not norm_ai:
        return True
    tokens_man = set(norm_man.split())
    tokens_ai = set(norm_ai.split())
    if not tokens_man or not tokens_ai:
        return True
    intersection = tokens_man.intersection(tokens_ai)
    similarity = len(intersection) / len(tokens_man)
    ratio = SequenceMatcher(None, norm_man, norm_ai).ratio()
    return similarity >= 0.9 or ratio >= 0.9

def main():
    print("=== Testing Minimum-Length / Anti-Copy-Paste Rule on Short Entries ===")
    test_cases = [
        ("Cold", "Patient might have upper respiratory infection", "Determination: 'Cold'"),
        ("ORS", "Prescribe oral hydration solution", "Medication: 'ORS'"),
        ("Dolo 650", "Recommend paracetamol 650mg tablet", "Medication: 'Dolo 650'"),
        ("Common cold", "Upper respiratory tract infection", "Determination: 'Common cold'"),
        ("Viral URTI", "Upper respiratory tract infection", "Determination: 'Viral URTI'"),
    ]
    for manual, ai, label in test_cases:
        res = is_too_similar_current(manual, ai)
        length = len(manual.strip())
        print(f"[{label}] text='{manual}' (len={length}) -> is_too_similar={res} (Blocked by len < 10: {length < 10})")

    print("\n=== Building Clinician Encounter in Test DB ===")
    client = TestClient(app)
    # Login as dr-martinez
    login_res = client.post("/api/v1/auth/login", json={"username": "dr-martinez", "password": "dev_clinician_pass"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    csrf = login_res.cookies.get("csrf_token")

    # Connect to clinical_scribe_test as scribe_app
    conn = psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "clinical_scribe_test"),
        user=os.environ.get("POSTGRES_USER", "scribe_app"),
        password=os.environ.get("POSTGRES_PASSWORD", "changeme_in_local_env_only"),
        autocommit=True,
    )

    enc_id = str(uuid.uuid4())
    conn.execute("SELECT set_config('app.current_user_id', 'dr-martinez', false)")
    conn.execute("SELECT set_config('app.current_role_id', 'clinician', false)")
    conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at,
             started_at, state)
        VALUES (%s, %s, %s, 'granted', now(), now(), 'medication_review')
        """,
        (enc_id, "dr-martinez", "patient-round7-repro"),
    )

    # Note: grounded S and O confirmed, two flagged assessment statements (requires_review), a plan, no medications
    note_content = {
        "encounter_id": enc_id,
        "model": {"name": "test-llm", "quant": "Q4", "prompt_version": "v1"},
        "sections": {
            "subjective": {
                "statements": [
                    {"id": "s_subj", "text": "Patient reports runny nose and mild sore throat for 3 days.", "grounded": True, "confirmed": True}
                ]
            },
            "objective": {
                "statements": [
                    {"id": "s_obj", "text": "Nasal mucosa erythematous, no exudate on tonsils.", "grounded": True, "confirmed": True}
                ]
            },
            "assessment": {
                "statements": [
                    {
                        "id": "stmt_flagged_1",
                        "text": "Possible viral respiratory illness",
                        "risk_tier": "requires_review",
                        "grounded": True
                    },
                    {
                        "id": "stmt_flagged_2",
                        "text": "Unspecified upper respiratory condition",
                        "risk_tier": "requires_review",
                        "grounded": True
                    }
                ]
            },
            "plan": {
                "statements": [
                    {"id": "s_plan", "text": "Hydration, rest, symptom management.", "grounded": True, "confirmed": True}
                ]
            }
        },
        "medications": [],
        "safety_flags": [],
        "grounding": {"statements_total": 4, "ungrounded": 0, "ungrounded_ids": []}
    }

    conn.execute(
        """
        INSERT INTO note_versions
            (id, encounter_id, version, source, content_jsonb, model_name, model_hash, prompt_version, created_at)
        VALUES (%s, %s, 1, 'model_generation', %s::jsonb, 'test', 'hash', 'v1', now())
        """,
        (str(uuid.uuid4()), enc_id, json.dumps(note_content)),
    )
    conn.close()

    print(f"Created encounter {enc_id} in clinical_scribe_test")

    print("\n=== Calling /api/v1/encounters/{id}/sign with determinations 'Common cold' and 'Viral URTI' ===")
    sign_payload = {
        "statement_determinations": {
            "stmt_flagged_1": "Common cold",
            "stmt_flagged_2": "Viral URTI"
        },
        "medication_entries": {},
        "acknowledged_flags": []
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    if csrf:
        headers["X-CSRF-Token"] = csrf
    cookies = {"csrf_token": csrf} if csrf else {}

    resp = client.post(
        f"/api/v1/encounters/{enc_id}/sign",
        json=sign_payload,
        headers=headers,
        cookies=cookies
    )

    print(f"Response status: {resp.status_code}")
    print(f"Response headers: {resp.headers}")
    print(f"Full response body: {resp.text}")

if __name__ == "__main__":
    main()
