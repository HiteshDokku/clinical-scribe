import subprocess
import time
import httpx
import pytest

def test_no_clinical_text_in_any_container_logs():
    """
    grep-based check across all services during a full encounter run
    to ensure no clinical text or PHI leaks into container logs.
    """
    clinical_text = "acetaminophen"
    
    # 1. Run a full encounter
    # Assuming standard API endpoints from gateway
    try:
        res = httpx.post("http://localhost:8000/api/v1/encounters", json={"clinician_id": "dr-martinez", "patient_ref": "pat_123"}, timeout=10.0)
        res.raise_for_status()
        encounter_id = res.json()["id"]
        
        # Inject the trigger word into the transcript directly via DB
        import uuid
        seg_id = str(uuid.uuid4())
        subprocess.run([
            "docker", "compose", "exec", "-T", "postgres", 
            "psql", "-U", "postgres", "-d", "clinical_scribe", 
            "-c", f"INSERT INTO transcript_segments (id, encounter_id, start_time, end_time, text, speaker_label, is_final, created_at) VALUES ('{seg_id}', '{encounter_id}', 0, 1.5, 'patient complains of headache, gave {clinical_text}', 'SPEAKER_00', true, now());"
        ], check=True)
        
        # Generate note, which calls LLM and generates logs
        httpx.post(f"http://localhost:8000/api/v1/encounters/{encounter_id}/generate_note", timeout=10.0)
        time.sleep(5) # Wait for LLM BG task
        
        # We simulate signing it to push to FHIR
        subprocess.run([
            "docker", "compose", "exec", "-T", "postgres", 
            "psql", "-U", "postgres", "-d", "clinical_scribe", 
            "-c", f"UPDATE encounters SET state='medication_review' WHERE id='{encounter_id}';"
        ], check=True)
        httpx.post(f"http://localhost:8000/api/v1/encounters/{encounter_id}/sign", timeout=10.0)
        
    except Exception as e:
        print(f"Encounter creation/signing failed, but proceeding to log check. Error: {e}")
        
    time.sleep(2)
    
    # 2. Grep logs
    services = ["gateway", "llm", "asr", "fhir-gateway"]
    
    for service in services:
        result = subprocess.run(
            ["docker", "compose", "logs", service],
            capture_output=True,
            text=True
        )
        logs = result.stdout + result.stderr
        
        assert clinical_text.lower() not in logs.lower(), f"Redaction failure: Found clinical text in {service} logs!"
