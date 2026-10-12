"""Part 8 Positive-Path Tests against Real Safety Service & Test Database.
Every test is labelled [real-service] or [mocked].
Guarded by tests/conftest.py to ensure it runs ONLY against clinical_scribe_test.
"""
import pytest
import uuid
import json
from fastapi.testclient import TestClient
from src.main import app
from tests.gateway.test_risk_gate_end_to_end import access_token, insert_encounter_and_note

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper to insert and query encounters in the test database
# ---------------------------------------------------------------------------
def create_test_note(pg_conn, token, state="medication_review", stmts=None, meds=None):
    if stmts is None:
        stmts = [
            {"id": "stmt_1", "text": "Suspected viral illness", "risk_tier": "requires_review", "statement_type": "inferred_diagnosis"},
            {"id": "stmt_2", "text": "Upper respiratory symptoms", "risk_tier": "requires_review", "statement_type": "inferred_diagnosis"},
        ]
    if meds is None:
        meds = []
    return insert_encounter_and_note(pg_conn, token, state=state, stmts=stmts, meds=meds)


# ---------------------------------------------------------------------------
# Test 8a: Cold case, no meds, determinations "Common cold" and "Cold" -> sign succeeds
# Label: [real-service] (Safety service unmocked, test DB)
# ---------------------------------------------------------------------------
def test_8a_cold_case_no_meds_determinations_succeed(pg_conn, access_token):
    token, csrf = access_token
    stmts = [
        {"id": "stmt_1", "text": "Suspected respiratory infection", "risk_tier": "requires_review", "statement_type": "inferred_diagnosis"},
        {"id": "stmt_2", "text": "Possible viral rhinitis", "risk_tier": "requires_review", "statement_type": "inferred_diagnosis"},
    ]
    enc_id = create_test_note(pg_conn, token, stmts=stmts, meds=[])

    req_body = {
        "edits": {},
        "statement_determinations": {
            "stmt_1": "Common cold",
            "stmt_2": "Cold",
        },
        "medication_entries": {},
    }
    headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
    cookies = {"csrf_token": csrf}

    res = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body, headers=headers, cookies=cookies)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert res.json() == {"status": "signed"}


# ---------------------------------------------------------------------------
# Test 8b: Red-flag AI diagnosis + clinician's different determination -> sign succeeds, audit manual_override
# Label: [real-service] (Safety service unmocked, test DB)
# ---------------------------------------------------------------------------
def test_8b_red_flag_ai_diagnosis_clinician_override_succeeds(pg_conn, access_token):
    token, csrf = access_token
    stmts = [
        {"id": "stmt_rf", "text": "Acute pulmonary embolism", "risk_tier": "red_flag", "statement_type": "inferred_diagnosis"}
    ]
    enc_id = create_test_note(pg_conn, token, stmts=stmts, meds=[])

    req_body = {
        "edits": {},
        "statement_determinations": {
            "stmt_rf": "Pleuritic chest wall strain",
        },
        "medication_entries": {},
    }
    headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
    cookies = {"csrf_token": csrf}

    res = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body, headers=headers, cookies=cookies)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert res.json() == {"status": "signed"}

    # Verify audit log recorded manual_override with tier=red_flag
    audit_res = client.get(f"/api/v1/encounters/{enc_id}/audit", headers=headers, cookies=cookies)
    assert audit_res.status_code == 200
    audit_rows = audit_res.json()
    override_rows = [r for r in audit_rows if r["action"] == "manual_override"]
    assert len(override_rows) > 0, "Audit log must contain manual_override action"
    override = override_rows[0]
    diff = override.get("diff", {})
    assert diff.get("tier") == "red_flag"
    assert diff.get("clinician_text") == "Pleuritic chest wall strain"


# ---------------------------------------------------------------------------
# Test 8c: Red-flag AI diagnosis, no determination -> blocked with structured error
# Label: [real-service] (Safety service unmocked, test DB)
# ---------------------------------------------------------------------------
def test_8c_red_flag_ai_diagnosis_no_determination_blocked_structured(pg_conn, access_token):
    token, csrf = access_token
    stmts = [
        {"id": "stmt_rf", "text": "Acute myocardial infarction", "risk_tier": "red_flag", "statement_type": "inferred_diagnosis"}
    ]
    enc_id = create_test_note(pg_conn, token, stmts=stmts, meds=[])

    req_body = {
        "edits": {},
        "statement_determinations": {},
        "medication_entries": {},
    }
    headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
    cookies = {"csrf_token": csrf}

    res = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body, headers=headers, cookies=cookies)
    assert res.status_code == 400
    data = res.json()
    assert "detail" in data
    detail = data["detail"]
    assert detail["code"] == "VALIDATION_FAILED"
    assert len(detail["items"]) > 0
    item = detail["items"][0]
    assert item["kind"] == "statement"
    assert item["id"] == "stmt_rf"
    assert "needs your own determination" in item["reason"]


# ---------------------------------------------------------------------------
# Test 8d: Determination identical to AI text -> sign succeeds, audit flag present
# Label: [real-service] (Safety service unmocked, test DB)
# ---------------------------------------------------------------------------
def test_8d_determination_identical_to_ai_text_succeeds_with_audit_flag(pg_conn, access_token):
    token, csrf = access_token
    stmts = [
        {"id": "stmt_rf", "text": "Severe asthma exacerbation", "risk_tier": "red_flag", "statement_type": "inferred_diagnosis"}
    ]
    enc_id = create_test_note(pg_conn, token, stmts=stmts, meds=[])

    req_body = {
        "edits": {},
        "statement_determinations": {
            "stmt_rf": "Severe asthma exacerbation",
        },
        "medication_entries": {},
    }
    headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
    cookies = {"csrf_token": csrf}

    res = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body, headers=headers, cookies=cookies)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert res.json() == {"status": "signed"}

    # Verify audit log contains matches_ai_draft=True flag and score in manual_override
    audit_res = client.get(f"/api/v1/encounters/{enc_id}/audit", headers=headers, cookies=cookies)
    assert audit_res.status_code == 200
    audit_rows = audit_res.json()
    override_rows = [r for r in audit_rows if r["action"] == "manual_override"]
    assert len(override_rows) > 0, "Audit log must contain manual_override action"
    override = override_rows[0]
    diff = override.get("diff", {})
    assert diff.get("matches_ai_draft") is True, f"Expected matches_ai_draft=True, got {diff}"
    assert diff.get("ai_similarity_score", 0) >= 0.9


# ---------------------------------------------------------------------------
# Test 8e: Antibiotic + manual entry "Amoxicillin 500 TDS" -> succeeds; none -> blocked
# Label: [real-service] (Safety service unmocked, test DB)
# ---------------------------------------------------------------------------
def test_8e_antibiotic_manual_entry_flow(pg_conn, access_token):
    token, csrf = access_token
    meds = [
        {"id": "med_abx", "verbatim": "Amoxicillin", "needs_manual_confirmation": True, "flags": []}
    ]
    enc_id = create_test_note(pg_conn, token, stmts=[], meds=meds)

    headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
    cookies = {"csrf_token": csrf}

    # Case 1: No manual entry -> blocked
    res_none = client.post(
        f"/api/v1/encounters/{enc_id}/sign",
        json={"edits": {}, "statement_determinations": {}, "medication_entries": {}},
        headers=headers,
        cookies=cookies,
    )
    assert res_none.status_code == 400
    detail = res_none.json()["detail"]
    assert detail["code"] == "VALIDATION_FAILED"
    assert any(it["id"] == "med_abx" for it in detail["items"])

    # Case 2: Manual entry "Amoxicillin 500 TDS" -> succeeds
    res_entry = client.post(
        f"/api/v1/encounters/{enc_id}/sign",
        json={
            "edits": {},
            "statement_determinations": {},
            "medication_entries": {"med_abx": "Amoxicillin 500 TDS"},
        },
        headers=headers,
        cookies=cookies,
    )
    assert res_entry.status_code == 200
    assert res_entry.json() == {"status": "signed"}


# ---------------------------------------------------------------------------
# Test 8f: Medication entry "ORS" and "Dolo 650" -> succeed
# Label: [real-service] (Safety service unmocked, test DB)
# ---------------------------------------------------------------------------
def test_8f_short_medication_entries_ors_dolo650(pg_conn, access_token):
    token, csrf = access_token
    meds = [
        {"id": "med_1", "verbatim": "Oral Rehydration Salts", "needs_manual_confirmation": True, "flags": []},
        {"id": "med_2", "verbatim": "Paracetamol 650", "needs_manual_confirmation": True, "flags": []},
    ]
    enc_id = create_test_note(pg_conn, token, stmts=[], meds=meds)

    headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
    cookies = {"csrf_token": csrf}

    res = client.post(
        f"/api/v1/encounters/{enc_id}/sign",
        json={
            "edits": {},
            "statement_determinations": {},
            "medication_entries": {
                "med_1": "ORS",
                "med_2": "Dolo 650",
            },
        },
        headers=headers,
        cookies=cookies,
    )
    assert res.status_code == 200, f"Expected 200 for ORS / Dolo 650, got {res.status_code}: {res.text}"
    assert res.json() == {"status": "signed"}


# ---------------------------------------------------------------------------
# Test 8g: Interaction pair from table + acknowledgement -> succeeds; without -> blocked;
#          same pair typed manually still flags
# Label: [real-service] (Safety service unmocked, test DB)
# ---------------------------------------------------------------------------
def test_8g_interaction_pair_flow(pg_conn, access_token):
    token, csrf = access_token
    headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
    cookies = {"csrf_token": csrf}

    # Case 1: Interacting pair unacknowledged -> blocked
    meds_flagged = [
        {
            "id": "med_spar",
            "verbatim": "sparfloxacin",
            "needs_manual_confirmation": True,
            "flags": [{"severity": "contraindicated", "message": "Severe QT prolongation with erythromycin"}],
        },
        {
            "id": "med_ery",
            "verbatim": "erythromycin",
            "needs_manual_confirmation": True,
            "flags": [{"severity": "contraindicated", "message": "Severe QT prolongation with sparfloxacin"}],
        },
    ]
    enc_id_unack = create_test_note(pg_conn, token, stmts=[], meds=meds_flagged)

    res_unack = client.post(
        f"/api/v1/encounters/{enc_id_unack}/sign",
        json={
            "edits": {},
            "statement_determinations": {},
            "medication_entries": {
                "med_spar": "sparfloxacin 200mg",
                "med_ery": "erythromycin 500mg",
            },
        },
        headers=headers,
        cookies=cookies,
    )
    assert res_unack.status_code == 400
    detail = res_unack.json()["detail"]
    assert detail["code"] == "VALIDATION_FAILED"
    assert any(it["kind"] == "interaction" for it in detail["items"])

    # Case 2: Clinician acknowledges the interaction flags -> succeeds
    # Acknowledge in audit
    client.post(f"/api/v1/encounters/{enc_id_unack}/acknowledge-flag", json={"flag_id": "med_spar:0"}, headers=headers, cookies=cookies)
    client.post(f"/api/v1/encounters/{enc_id_unack}/acknowledge-flag", json={"flag_id": "med_ery:0"}, headers=headers, cookies=cookies)

    sign_payload = {
        "edits": {},
        "statement_determinations": {},
        "medication_entries": {
            "med_spar": "sparfloxacin 200mg",
            "med_ery": "erythromycin 500mg",
        },
        "acknowledged_flags": ["med_spar:0", "med_ery:0"],
    }
    print(f"\n[ACTUAL JSON BODY SENT TO /sign]:\n{json.dumps(sign_payload, indent=2)}")

    res_ack = client.post(
        f"/api/v1/encounters/{enc_id_unack}/sign",
        json=sign_payload,
        headers=headers,
        cookies=cookies,
    )
    assert res_ack.status_code == 200, f"res_ack failed: {res_ack.status_code} {res_ack.text}"
    assert res_ack.json() == {"status": "signed"}

    # Case 3: Same pair typed manually in medication_entries from scratch
    # Even if original note had harmless medications, typing interacting pair manually flags
    meds_safe = [
        {"id": "med_a", "verbatim": "cetirizine", "needs_manual_confirmation": True, "flags": []},
        {"id": "med_b", "verbatim": "paracetamol", "needs_manual_confirmation": True, "flags": []},
    ]
    enc_id_manual = create_test_note(pg_conn, token, stmts=[], meds=meds_safe)

    res_manual_flag = client.post(
        f"/api/v1/encounters/{enc_id_manual}/sign",
        json={
            "edits": {},
            "statement_determinations": {},
            "medication_entries": {
                "med_a": "sparfloxacin 400mg OD",
                "med_b": "erythromycin 500mg QDS",
            },
        },
        headers=headers,
        cookies=cookies,
    )
    assert res_manual_flag.status_code == 400
    detail = res_manual_flag.json()["detail"]
    assert any(it["kind"] == "interaction" for it in detail["items"])


# ---------------------------------------------------------------------------
# Test 8h: Manual diagnosis, no medications -> sign succeeds
# Label: [real-service] (Safety service unmocked, test DB)
# ---------------------------------------------------------------------------
def test_8h_manual_diagnosis_no_medications_succeeds(pg_conn, access_token):
    token, csrf = access_token
    enc_id = create_test_note(pg_conn, token, stmts=[], meds=[])

    headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
    cookies = {"csrf_token": csrf}

    res = client.post(
        f"/api/v1/encounters/{enc_id}/sign",
        json={
            "edits": {"assessment": "Acute viral bronchitis without complications"},
            "statement_determinations": {},
            "medication_entries": {},
        },
        headers=headers,
        cookies=cookies,
    )
    assert res.status_code == 200
    assert res.json() == {"status": "signed"}
