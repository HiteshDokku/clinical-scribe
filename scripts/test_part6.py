import os
import uuid
import json
import psycopg
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.main import app

def main():
    print("=== Part 6: Audit Dashboard Test ===")
    client = TestClient(app)
    login_res = client.post("/api/v1/auth/login", json={"username": "dr-martinez", "password": "dev_clinician_pass"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    csrf = login_res.cookies.get("csrf_token")

    # Connect to clinical_scribe_test
    conn = psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "clinical_scribe_test"),
        user=os.environ.get("POSTGRES_USER", "scribe_app"),
        password=os.environ.get("POSTGRES_PASSWORD", "changeme_in_local_env_only"),
        autocommit=True,
    )
    conn.execute("SELECT set_config('app.current_user_id', 'dr-martinez', false)")
    conn.execute("SELECT set_config('app.current_role_id', 'clinician', false)")

    now = datetime.now(timezone.utc)
    t_old = now - timedelta(hours=2)
    t_new = now - timedelta(hours=1)

    # 1. Unsigned encounter
    enc_unsigned = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at,
             started_at, state)
        VALUES (%s, 'dr-martinez', 'patient-unsigned', 'granted', now(), %s, 'medication_review')
        """,
        (enc_unsigned, now),
    )

    # 2. Signed encounter 1 (older)
    enc_signed_1 = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at,
             started_at, state)
        VALUES (%s, 'dr-martinez', 'patient-signed-1', 'granted', now(), %s, 'signed')
        """,
        (enc_signed_1, t_old),
    )
    note_1 = {
        "encounter_id": enc_signed_1,
        "sections": {
            "assessment": {
                "statements": [{"id": "s1", "text": "Acute viral bronchitis without complications", "risk_tier": "common"}]
            }
        }
    }
    conn.execute(
        """
        INSERT INTO note_versions
            (id, encounter_id, version, source, content_jsonb, model_name, model_hash, prompt_version, created_at)
        VALUES (%s, %s, 1, 'clinician_edit', %s::jsonb, 'test', 'h1', 'v1', %s)
        """,
        (str(uuid.uuid4()), enc_signed_1, json.dumps(note_1), t_old),
    )

    # 3. Signed encounter 2 (newer)
    enc_signed_2 = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at,
             started_at, state)
        VALUES (%s, 'dr-martinez', 'patient-signed-2', 'granted', now(), %s, 'signed')
        """,
        (enc_signed_2, t_new),
    )
    note_2 = {
        "encounter_id": enc_signed_2,
        "sections": {
            "assessment": {
                "statements": [
                    {"id": "s1", "text": "Streptococcal pharyngitis confirmed by throat swab"},
                    {"id": "s2", "text": "Associated mild dehydration"}
                ]
            }
        }
    }
    conn.execute(
        """
        INSERT INTO note_versions
            (id, encounter_id, version, source, content_jsonb, model_name, model_hash, prompt_version, created_at)
        VALUES (%s, %s, 1, 'clinician_edit', %s::jsonb, 'test', 'h2', 'v1', %s)
        """,
        (str(uuid.uuid4()), enc_signed_2, json.dumps(note_2), t_new),
    )
    conn.close()

    headers = {"Authorization": f"Bearer {token}"}
    if csrf:
        headers["X-CSRF-Token"] = csrf
    cookies = {"csrf_token": csrf} if csrf else {}

    res = client.get("/api/v1/encounters", headers=headers, cookies=cookies)
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, res.text
    data = res.json()
    print(f"Total returned encounters: {len(data)}")
    print(f"Payload: {json.dumps(data, indent=2)}")

    # Verify only signed encounters are returned
    returned_ids = [e["id"] for e in data]
    assert enc_unsigned not in returned_ids, f"Unsigned encounter {enc_unsigned} leaked into dashboard!"
    assert enc_signed_2 in returned_ids, "Newer signed encounter missing!"
    assert enc_signed_1 in returned_ids, "Older signed encounter missing!"

    # Verify order: newest first
    idx_new = returned_ids.index(enc_signed_2)
    idx_old = returned_ids.index(enc_signed_1)
    assert idx_new < idx_old, f"Order incorrect: newer ({idx_new}) must precede older ({idx_old})"

    # Verify summaries
    for enc in data:
        summary = enc.get("confirmed_diagnosis_summary", "")
        print(f"Encounter {enc['id']} ({enc['patient_ref']}) summary: '{summary}'")
        assert summary, "Summary must be non-empty"
        assert "Pending" not in summary, "'Pending' found in summary!"
        assert "pending" not in summary.lower(), "'pending' found in summary!"

    raw_text = res.text
    assert "Pending" not in raw_text, "'Pending' found in response body!"
    print("ALL PART 6 AUDIT DASHBOARD ASSERTIONS PASSED!")

if __name__ == "__main__":
    main()
