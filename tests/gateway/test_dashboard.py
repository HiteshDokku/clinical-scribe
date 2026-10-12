"""Tests for audit dashboard encounters endpoint and row summary formatter.
Label: [real-service]
"""
import uuid
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.main import app, format_diagnosis_summary
from tests.gateway.test_risk_gate_end_to_end import access_token

client = TestClient(app)


def test_format_diagnosis_summary_row_formatter():
    """Unit test verifying format_diagnosis_summary handles empty, 'pending', normal, and long strings."""
    # Empty / None cases
    assert format_diagnosis_summary(None) == "No diagnosis recorded"
    assert format_diagnosis_summary("") == "No diagnosis recorded"
    assert format_diagnosis_summary("   ") == "No diagnosis recorded"

    # 'Pending' variants must NEVER be returned
    assert format_diagnosis_summary("Pending") == "No diagnosis recorded"
    assert format_diagnosis_summary("pending") == "No diagnosis recorded"
    assert format_diagnosis_summary("PENDING") == "No diagnosis recorded"
    assert format_diagnosis_summary("  Pending  ") == "No diagnosis recorded"

    # Normal diagnosis text
    assert format_diagnosis_summary("Acute viral nasopharyngitis") == "Acute viral nasopharyngitis"

    # Long text truncation (~80 chars)
    long_diag = "Patient presents with persistent severe bilateral acute exacerbation of chronic obstructive pulmonary disease"
    formatted = format_diagnosis_summary(long_diag)
    assert len(formatted) <= 80
    assert formatted.endswith("...")
    assert "Patient presents" in formatted


def test_dashboard_signed_only_newest_first_and_no_pending(pg_conn, access_token):
    """Integration test verifying GET /api/v1/encounters returns only signed encounters,
    newest first, limit 10 post-filter, with diagnosis summary and zero 'Pending'.
    """
    token, csrf = access_token
    headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
    cookies = {"csrf_token": csrf}

    now = datetime.now(timezone.utc)
    t_old = now - timedelta(hours=2)
    t_new = now - timedelta(hours=1)

    # 1. Insert Unsigned encounter (must NOT appear on dashboard)
    enc_unsigned = str(uuid.uuid4())
    pg_conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at, started_at, state)
        VALUES (%s, 'dr-martinez', 'patient-unsigned', 'granted', now(), %s, 'medication_review')
        """,
        (enc_unsigned, now),
    )

    # 2. Insert Signed encounter 1 (older)
    enc_signed_1 = str(uuid.uuid4())
    pg_conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at, started_at, state)
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
    pg_conn.execute(
        """
        INSERT INTO note_versions
            (id, encounter_id, version, source, content_jsonb, model_name, model_hash, prompt_version, created_at)
        VALUES (%s, %s, 1, 'clinician_edit', %s::jsonb, 'test', 'h1', 'v1', %s)
        """,
        (str(uuid.uuid4()), enc_signed_1, json.dumps(note_1), t_old),
    )

    # 3. Insert Signed encounter 2 (newer)
    enc_signed_2 = str(uuid.uuid4())
    pg_conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at, started_at, state)
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
    pg_conn.execute(
        """
        INSERT INTO note_versions
            (id, encounter_id, version, source, content_jsonb, model_name, model_hash, prompt_version, created_at)
        VALUES (%s, %s, 1, 'clinician_edit', %s::jsonb, 'test', 'h2', 'v1', %s)
        """,
        (str(uuid.uuid4()), enc_signed_2, json.dumps(note_2), t_new),
    )

    # Call dashboard endpoint
    res = client.get("/api/v1/encounters", headers=headers, cookies=cookies)
    assert res.status_code == 200, f"Dashboard failed: {res.status_code} {res.text}"
    encounters = res.json()

    # Assertions
    returned_ids = [e["id"] for e in encounters]
    assert enc_unsigned not in returned_ids, "Unsigned encounter must be excluded"
    assert enc_signed_1 in returned_ids, "Signed encounter 1 must be present"
    assert enc_signed_2 in returned_ids, "Signed encounter 2 must be present"

    # Newest signed must come before older signed
    idx_1 = returned_ids.index(enc_signed_1)
    idx_2 = returned_ids.index(enc_signed_2)
    assert idx_2 < idx_1, f"Newer encounter ({enc_signed_2}) must appear before older ({enc_signed_1})"

    # Verify summaries and absolute absence of 'Pending'
    for enc in encounters:
        assert enc["state"] == "signed", "All returned encounters must be in signed state"
        summary = enc.get("confirmed_diagnosis_summary", "")
        assert summary != "", "Summary should not be empty"
        assert "pending" not in summary.lower(), f"Summary contained 'pending': {summary}"
