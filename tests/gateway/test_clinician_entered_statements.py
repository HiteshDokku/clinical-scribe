import pytest
import uuid
import json
import re
import jwt
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.fixture
def auth_tokens():
    res_c1 = client.post("/api/v1/auth/login", json={"username": "dr-martinez", "password": "dev_clinician_pass"})
    assert res_c1.status_code == 200
    c1_token = res_c1.json()["access_token"]
    c1_csrf = res_c1.cookies.get("csrf_token")
    c1_uid = jwt.decode(c1_token, options={"verify_signature": False})["sub"]

    res_c2 = client.post("/api/v1/auth/login", json={"username": "dr-jones", "password": "dev_clinician_pass"})
    assert res_c2.status_code == 200
    c2_token = res_c2.json()["access_token"]
    c2_csrf = res_c2.cookies.get("csrf_token")
    c2_uid = jwt.decode(c2_token, options={"verify_signature": False})["sub"]

    res_admin = client.post("/api/v1/auth/login", json={"username": "admin", "password": "dev_admin_pass"})
    assert res_admin.status_code == 200
    admin_token = res_admin.json()["access_token"]
    admin_csrf = res_admin.cookies.get("csrf_token")
    admin_uid = jwt.decode(admin_token, options={"verify_signature": False})["sub"]

    res_auditor = client.post("/api/v1/auth/login", json={"username": "auditor", "password": "dev_admin_pass"})
    assert res_auditor.status_code == 200
    auditor_token = res_auditor.json()["access_token"]
    auditor_csrf = res_auditor.cookies.get("csrf_token")
    auditor_uid = jwt.decode(auditor_token, options={"verify_signature": False})["sub"]

    return {
        "c1": {"token": c1_token, "csrf": c1_csrf, "user_id": c1_uid},
        "c2": {"token": c2_token, "csrf": c2_csrf, "user_id": c2_uid},
        "admin": {"token": admin_token, "csrf": admin_csrf, "user_id": admin_uid},
        "auditor": {"token": auditor_token, "csrf": auditor_csrf, "user_id": auditor_uid},
    }

def create_test_encounter_with_note(pg_conn, clinician_id, state="diagnosis_review", objective_insufficient=True):
    enc_id = str(uuid.uuid4())
    pg_conn.execute("SELECT set_config('app.current_user_id', %s, false)", (clinician_id,))
    pg_conn.execute("SELECT set_config('app.current_role_id', 'clinician', false)")
    pg_conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at, started_at, state)
        VALUES (%s, %s, %s, 'granted', now(), now(), %s)
        """,
        (enc_id, clinician_id, "test-patient", state)
    )

    note_content = {
        "encounter_id": enc_id,
        "model": {"name": "llama3", "quant": "q4_k_m", "prompt_version": "v1"},
        "sections": {
            "subjective": {"statements": [], "insufficient_content": False},
            "objective": {
                "statements": [],
                "insufficient_content": objective_insufficient,
                "reason": "Not discussed in this consultation" if objective_insufficient else None
            },
            "assessment": {
                "statements": [
                    {
                        "id": "stmt_a1",
                        "text": "Common cold",
                        "statement_type": "inferred_diagnosis",
                        "risk_tier": "common",
                        "evidence": []
                    }
                ],
                "insufficient_content": False
            },
            "plan": {"statements": [], "insufficient_content": False}
        },
        "medications": [],
        "safety_flags": [],
        "grounding": {"statements_total": 1, "ungrounded": 0, "ungrounded_ids": []}
    }

    pg_conn.execute(
        """
        INSERT INTO note_versions
            (id, encounter_id, version, source, content_jsonb, model_name, model_hash, prompt_version, created_at)
        VALUES (%s, %s, 1, 'model_generation', %s::jsonb, 'llama3', 'hash123', 'v1', now())
        """,
        (str(uuid.uuid4()), enc_id, json.dumps(note_content))
    )
    pg_conn.commit()
    return enc_id

def test_3a_clinician_adds_objective_statement(pg_conn, auth_tokens):
    """3a: clinician adds an Objective statement: 200, note contains it, insufficient_content=false, audit entry has the right actor."""
    c1 = auth_tokens["c1"]
    enc_id = create_test_encounter_with_note(pg_conn, c1["user_id"], state="diagnosis_review", objective_insufficient=True)

    body = {"section": "objective", "text": "BP 120/80, temp 37.2 C"}
    res = client.post(
        f"/api/v1/encounters/{enc_id}/statements",
        json=body,
        headers={"Authorization": f"Bearer {c1['token']}", "X-CSRF-Token": c1["csrf"]},
        cookies={"csrf_token": c1["csrf"]}
    )

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    obj_sec = data["sections"]["objective"]
    assert obj_sec["insufficient_content"] is False
    assert len(obj_sec["statements"]) == 1

    added_stmt = obj_sec["statements"][0]
    assert added_stmt["text"] == "BP 120/80, temp 37.2 C"
    assert added_stmt["statement_type"] == "clinician_entered"
    assert added_stmt["authored_by"] == c1["user_id"]
    assert added_stmt["evidence"] == []
    assert "created_at" in added_stmt

    # Verify audit_log entry
    pg_conn.execute("SELECT set_config('app.current_user_id', %s, false)", (c1["user_id"],))
    pg_conn.execute("SELECT set_config('app.current_role_id', 'clinician', false)")
    cur = pg_conn.execute(
        "SELECT actor, action, diff_jsonb FROM audit_log WHERE encounter_id = %s AND action = 'statement_added'",
        (enc_id,)
    )
    rows = cur.fetchall()
    assert len(rows) >= 1
    actor, action, diff = rows[0]
    assert actor == c1["user_id"]
    assert action == "statement_added"
    assert diff["section"] == "objective"
    assert diff["text"] == "BP 120/80, temp 37.2 C"

def test_3b_another_clinician_encounter_404(pg_conn, auth_tokens):
    """3b: another clinician's encounter: 404."""
    c1 = auth_tokens["c1"]
    c2 = auth_tokens["c2"]
    enc_id = create_test_encounter_with_note(pg_conn, c1["user_id"], state="diagnosis_review")

    body = {"section": "objective", "text": "Heart rate 75 bpm"}
    res = client.post(
        f"/api/v1/encounters/{enc_id}/statements",
        json=body,
        headers={"Authorization": f"Bearer {c2['token']}", "X-CSRF-Token": c2["csrf"]},
        cookies={"csrf_token": c2["csrf"]}
    )
    assert res.status_code == 404, f"Expected 404, got {res.status_code}: {res.text}"

def test_3c_auditor_and_admin_403(pg_conn, auth_tokens):
    """3c: auditor and admin: 403."""
    c1 = auth_tokens["c1"]
    admin = auth_tokens["admin"]
    auditor = auth_tokens["auditor"]
    enc_id = create_test_encounter_with_note(pg_conn, c1["user_id"], state="diagnosis_review")

    body = {"section": "objective", "text": "Heart rate 75 bpm"}

    # Admin attempt
    res_admin = client.post(
        f"/api/v1/encounters/{enc_id}/statements",
        json=body,
        headers={"Authorization": f"Bearer {admin['token']}", "X-CSRF-Token": admin["csrf"]},
        cookies={"csrf_token": admin["csrf"]}
    )
    assert res_admin.status_code == 403, f"Expected admin 403, got {res_admin.status_code}: {res_admin.text}"

    # Auditor attempt
    res_aud = client.post(
        f"/api/v1/encounters/{enc_id}/statements",
        json=body,
        headers={"Authorization": f"Bearer {auditor['token']}", "X-CSRF-Token": auditor["csrf"]},
        cookies={"csrf_token": auditor["csrf"]}
    )
    assert res_aud.status_code == 403, f"Expected auditor 403, got {res_aud.status_code}: {res_aud.text}"

def test_3d_signed_encounter_rejected(pg_conn, auth_tokens):
    """3d: signed encounter: rejected."""
    c1 = auth_tokens["c1"]
    enc_id = create_test_encounter_with_note(pg_conn, c1["user_id"], state="signed")

    body = {"section": "objective", "text": "BP 130/85"}
    res = client.post(
        f"/api/v1/encounters/{enc_id}/statements",
        json=body,
        headers={"Authorization": f"Bearer {c1['token']}", "X-CSRF-Token": c1["csrf"]},
        cookies={"csrf_token": c1["csrf"]}
    )
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"

def test_3e_text_under_3_non_space_chars_422(pg_conn, auth_tokens):
    """3e: text under 3 non-space characters: 422."""
    c1 = auth_tokens["c1"]
    enc_id = create_test_encounter_with_note(pg_conn, c1["user_id"], state="diagnosis_review")

    for short_text in ["", "  ", " a ", "ab", "  a b  "]:
        # "a b" has 2 non-space chars
        if len(re.sub(r'\s', '', short_text)) < 3:
            res = client.post(
                f"/api/v1/encounters/{enc_id}/statements",
                json={"section": "objective", "text": short_text},
                headers={"Authorization": f"Bearer {c1['token']}", "X-CSRF-Token": c1["csrf"]},
                cookies={"csrf_token": c1["csrf"]}
            )
            assert res.status_code == 422, f"Expected 422 for {repr(short_text)}, got {res.status_code}"

def test_3f_body_authored_by_is_ignored(pg_conn, auth_tokens):
    """3f: a body containing authored_by is ignored (actor still comes from the JWT)."""
    c1 = auth_tokens["c1"]
    enc_id = create_test_encounter_with_note(pg_conn, c1["user_id"], state="medication_review")

    # Send body with spoofed authored_by
    body = {
        "section": "objective",
        "text": "Temperature 36.8 C oral",
        "authored_by": "spoofed_dr_evil"
    }
    res = client.post(
        f"/api/v1/encounters/{enc_id}/statements",
        json=body,
        headers={"Authorization": f"Bearer {c1['token']}", "X-CSRF-Token": c1["csrf"]},
        cookies={"csrf_token": c1["csrf"]}
    )
    assert res.status_code == 200
    data = res.json()
    stmt = data["sections"]["objective"]["statements"][0]
    assert stmt["authored_by"] == c1["user_id"]
    assert stmt["authored_by"] != "spoofed_dr_evil"

def test_3g_sign_succeeds_with_clinician_entered_objective_no_evidence(pg_conn, auth_tokens):
    """3g: sign succeeds with a clinician_entered Objective statement and no evidence."""
    c1 = auth_tokens["c1"]
    enc_id = create_test_encounter_with_note(pg_conn, c1["user_id"], state="medication_review", objective_insufficient=True)

    # Add clinician-entered Objective statement
    res_add = client.post(
        f"/api/v1/encounters/{enc_id}/statements",
        json={"section": "objective", "text": "BP 120/80, temp 37.2 C"},
        headers={"Authorization": f"Bearer {c1['token']}", "X-CSRF-Token": c1["csrf"]},
        cookies={"csrf_token": c1["csrf"]}
    )
    assert res_add.status_code == 200
    note_data = res_add.json()
    assert note_data["sections"]["objective"]["statements"][0]["statement_type"] == "clinician_entered"
    assert note_data["sections"]["objective"]["statements"][0]["evidence"] == []

    # Sign the encounter
    sign_req = {
        "edits": {},
        "statement_determinations": {"stmt_a1": "Common cold"},
        "medication_entries": {},
        "acknowledged_flags": []
    }
    res_sign = client.post(
        f"/api/v1/encounters/{enc_id}/sign",
        json=sign_req,
        headers={"Authorization": f"Bearer {c1['token']}", "X-CSRF-Token": c1["csrf"]},
        cookies={"csrf_token": c1["csrf"]}
    )
    assert res_sign.status_code == 200, f"Expected 200 on sign, got {res_sign.status_code}: {res_sign.text}"
    sign_data = res_sign.json()
    assert sign_data["status"] == "signed"

    # Verify encounter state is signed
    pg_conn.execute("SELECT set_config('app.current_user_id', %s, false)", (c1["user_id"],))
    pg_conn.execute("SELECT set_config('app.current_role_id', 'clinician', false)")
    cur = pg_conn.execute("SELECT state FROM encounters WHERE id = %s", (enc_id,))
    row = cur.fetchone()
    assert row[0] == "signed"

def test_3h_section_state_transition_and_review_helper(pg_conn, auth_tokens):
    """3h: a reducer/helper test for the new section state."""
    c1 = auth_tokens["c1"]
    enc_id = create_test_encounter_with_note(pg_conn, c1["user_id"], state="diagnosis_review", objective_insufficient=True)

    # Initial state: Objective is insufficient with 0 statements
    res_init = client.get(
        f"/api/v1/encounters/{enc_id}",
        headers={"Authorization": f"Bearer {c1['token']}", "X-CSRF-Token": c1["csrf"]},
        cookies={"csrf_token": c1["csrf"]}
    )
    assert res_init.status_code == 200
    initial_note = res_init.json()["note"]
    assert initial_note["sections"]["objective"]["insufficient_content"] is True
    assert len(initial_note["sections"]["objective"]["statements"]) == 0

    # Clinician adds statement to Objective
    res_add = client.post(
        f"/api/v1/encounters/{enc_id}/statements",
        json={"section": "objective", "text": "Heart rate 72 bpm regular rhythm"},
        headers={"Authorization": f"Bearer {c1['token']}", "X-CSRF-Token": c1["csrf"]},
        cookies={"csrf_token": c1["csrf"]}
    )
    assert res_add.status_code == 200
    updated_note = res_add.json()

    # Section state reducer verification:
    # 1. insufficient_content transitions from True to False
    assert updated_note["sections"]["objective"]["insufficient_content"] is False
    # 2. reason is cleared
    assert updated_note["sections"]["objective"]["reason"] is None
    # 3. Exactly 1 statement present
    assert len(updated_note["sections"]["objective"]["statements"]) == 1
    # 4. Clinician-entered statement is marked confirmed / not ungrounded
    stmt = updated_note["sections"]["objective"]["statements"][0]
    assert stmt["statement_type"] == "clinician_entered"
    assert stmt["id"] not in updated_note.get("grounding", {}).get("ungrounded_ids", [])
    assert stmt["evidence"] == []
