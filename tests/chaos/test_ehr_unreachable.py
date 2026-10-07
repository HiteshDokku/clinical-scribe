import pytest
import subprocess
import time
import httpx

def test_ehr_unreachable_fallback_and_retry():
    """
    Block fhir-gateway's egress route, sign a note, 
    assert ehr_status: "queued_local", 
    assert retry succeeds once restored.
    """
    encounter_id = None
    try:
        # 1. Stop HAPI FHIR to block egress
        subprocess.run(["docker", "compose", "stop", "hapi-fhir"], check=True)
        
        # 2. Create encounter and put it into medication_review state
        res = httpx.post("http://localhost:8000/api/v1/encounters", json={"clinician_id": "dr-martinez", "patient_ref": "pat_123"}, timeout=5.0)
        res.raise_for_status()
        encounter_id = res.json()["id"]
        
        # Mocking the state transitions directly via DB or assuming we can force state
        # In this chaotic test, let's just use the sign endpoint. 
        # Wait, the sign endpoint requires state="medication_review". 
        # Let's forcefully change the state if we have to, or run it through the normal flow.
        
        # Actually, let's run the DB update directly since it's a test script 
        # hitting the external gateway, but we don't have all the complex LLM stubs here.
        # We can just do a postgres query to update the state to medication_review
        # AND insert a dummy note_version so fhir-gateway has something to push!
        subprocess.run([
            "docker", "compose", "exec", "-T", "postgres", 
            "psql", "-U", "postgres", "-d", "clinical_scribe", 
            "-c", f"UPDATE encounters SET state='medication_review' WHERE id='{encounter_id}';"
        ], check=True)
        
        import uuid
        dummy_note_id = str(uuid.uuid4())
        subprocess.run([
            "docker", "compose", "exec", "-T", "postgres", 
            "psql", "-U", "postgres", "-d", "clinical_scribe", 
            "-c", f"INSERT INTO note_versions (id, encounter_id, version, source, content_jsonb, model_name, model_hash, prompt_version, created_at) VALUES ('{dummy_note_id}', '{encounter_id}', 1, 'ai', '{{\"sections\": {{\"plan\": {{\"statements\": []}}}}}}', 'llama-3-8b-instruct', 'hash', 'v1', now());"
        ], check=True)
        
        # 3. Sign the note
        res = httpx.post(f"http://localhost:8000/api/v1/encounters/{encounter_id}/sign", timeout=5.0)
        res.raise_for_status()
        
        # 4. Wait for background task to fail and mark as queued_local
        status = "pending"
        for _ in range(10):
            res = httpx.get(f"http://localhost:8000/api/v1/encounters/{encounter_id}", timeout=5.0)
            status = res.json().get("ehr_status")
            if status == "queued_local":
                break
            time.sleep(1)
        
        assert status == "queued_local", f"Expected queued_local, got {status}"
        
        # 5. Restore HAPI FHIR
        subprocess.run(["docker", "compose", "start", "hapi-fhir"], check=True)
        # Give it a moment to boot, it can take up to 60 seconds
        for _ in range(60):
            try:
                res = httpx.get("http://localhost:8080/fhir/metadata", timeout=2.0)
                if res.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        
        # 6. Retry
        res = httpx.post(f"http://localhost:8000/api/v1/encounters/{encounter_id}/retry_sync", timeout=5.0)
        res.raise_for_status()
        
        # 7. Assert success
        for _ in range(10):
            res = httpx.get(f"http://localhost:8000/api/v1/encounters/{encounter_id}", timeout=5.0)
            status = res.json().get("ehr_status")
            if status == "synced":
                break
            time.sleep(1)
            
        assert status == "synced", f"Expected synced, got {status}"
        
    finally:
        # Ensure it's started for other tests
        subprocess.run(["docker", "compose", "start", "hapi-fhir"], check=False)
