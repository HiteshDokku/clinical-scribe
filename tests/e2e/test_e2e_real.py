import asyncio
import httpx
import uuid
import sys
import json
import time
import pytest

@pytest.mark.asyncio
async def test_multi_turn_encounter():
    async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
        # 1. Login
        res = await client.post("/auth/login", json={"username": "dr-martinez", "password": "dev_clinician_pass"})
        assert res.status_code == 200, res.text
        token = res.json()["access_token"]
        csrf = res.cookies.get("csrf_token")
        headers = {"Authorization": f"Bearer {token}", "X-User-Id": "dr-martinez", "X-Role-Id": "clinician", "X-CSRF-Token": csrf}
        
        # 2. Create encounter
        res = await client.post("/encounters", headers=headers, json={"clinician_id": "dr-martinez", "patient_ref": "E2E Test Patient"})
        assert res.status_code == 200, res.text
        enc_id = res.json()["id"]
        
        import subprocess
        # Hack to update state since there's no REST endpoint for it
        subprocess.run([
            "docker", "compose", "exec", "-T", "postgres", 
            "psql", "-U", "postgres", "-d", "clinical_scribe", 
            "-c", f"UPDATE encounters SET state='transcribing' WHERE id='{enc_id}'"
        ])
        
        # 3. Generate Note
        # We will submit a mock transcript that should trigger real extraction and diagnosis
        segments = [
            {"id": "seg_1", "speaker": "clinician", "start_ms": 0, "end_ms": 2000, "text": "Hi, what brings you in today?"},
            {"id": "seg_2", "speaker": "patient", "start_ms": 2000, "end_ms": 5000, "text": "I've been having severe chest pain radiating to my left arm, and I take Warfarin."},
        ]
        res = await client.post(f"/encounters/{enc_id}/generate", headers=headers, json={"segments": segments}, timeout=60.0)
        assert res.status_code == 200, res.text
            
        # Poll for completion
        for _ in range(60):
            res = await client.get(f"/encounters/{enc_id}", headers=headers)
            state = res.json()["state"]
            if state == "diagnosis_review":
                break
            await asyncio.sleep(2)
            
        assert state == "diagnosis_review", "Note generation timed out or failed."
            
        # Get note
        res = await client.get(f"/encounters/{enc_id}/note", headers=headers)
        note = res.json()
        print("\n--- RAW DIAGNOSE NOTE (MULTI) ---")
        print(json.dumps(note, indent=2))
        
        # 4. Confirm diagnosis
        confirmed_diagnosis = "Patient has severe chest pain radiating to left arm. Taking Warfarin."
        res = await client.post(f"/encounters/{enc_id}/confirm-diagnosis", headers=headers, json={"confirmed_diagnosis": confirmed_diagnosis}, timeout=120.0)
        assert res.status_code == 200, res.text
            
        # Poll for completion
        for _ in range(60):
            res = await client.get(f"/encounters/{enc_id}", headers=headers)
            state = res.json()["state"]
            if state == "medication_review":
                break
            await asyncio.sleep(2)
            
        assert state == "medication_review", "Prescription generation timed out or failed."
        
        # Get final note
        res = await client.get(f"/encounters/{enc_id}/note", headers=headers)
        final_note = res.json()
        print("\n--- RAW PRESCRIBE NOTE (MULTI) ---")
        print(json.dumps(final_note, indent=2))

@pytest.mark.asyncio
async def test_trivial_encounter():
    async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
        # 1. Login
        res = await client.post("/auth/login", json={"username": "dr-martinez", "password": "dev_clinician_pass"})
        assert res.status_code == 200, res.text
        token = res.json()["access_token"]
        csrf = res.cookies.get("csrf_token")
        headers = {"Authorization": f"Bearer {token}", "X-User-Id": "dr-martinez", "X-Role-Id": "clinician", "X-CSRF-Token": csrf}
        
        # 2. Create encounter
        res = await client.post("/encounters", headers=headers, json={"clinician_id": "dr-martinez", "patient_ref": "Trivial Patient"})
        assert res.status_code == 200, res.text
        enc_id = res.json()["id"]
        
        import subprocess
        # Hack to update state since there's no REST endpoint for it
        subprocess.run([
            "docker", "compose", "exec", "-T", "postgres", 
            "psql", "-U", "postgres", "-d", "clinical_scribe", 
            "-c", f"UPDATE encounters SET state='transcribing' WHERE id='{enc_id}'"
        ])
        
        # 3. Generate Note
        # Trivial transcript
        segments = [
            {"id": "seg_1", "speaker": "clinician", "start_ms": 0, "end_ms": 2000, "text": "Hi."},
            {"id": "seg_2", "speaker": "patient", "start_ms": 2000, "end_ms": 5000, "text": "Hello, see you later."},
        ]
        res = await client.post(f"/encounters/{enc_id}/generate", headers=headers, json={"segments": segments}, timeout=60.0)
        assert res.status_code == 200, res.text
            
        # Poll for completion
        for _ in range(60):
            res = await client.get(f"/encounters/{enc_id}", headers=headers)
            state = res.json()["state"]
            if state == "diagnosis_review":
                break
            await asyncio.sleep(2)
            
        assert state == "diagnosis_review", "Note generation timed out or failed."
            
        # Get note
        res = await client.get(f"/encounters/{enc_id}/note", headers=headers)
        note = res.json()
        print("\n--- RAW DIAGNOSE NOTE (TRIVIAL) ---")
        print(json.dumps(note, indent=2))
        assert note["grounding"]["statements_total"] == 0, "Expected 0 statements for trivial transcript"
        assert note["sections"]["subjective"]["insufficient_content"] is True
