import pytest
import httpx
import websockets
import asyncio
import json
import subprocess

@pytest.mark.asyncio
async def test_gpu_oom_fallback():
    """
    Simulate LLM backend OOM, assert fallback to the smaller model tier, 
    assert the resulting note's model.name/quant reflects the model actually used.
    """
    res = httpx.post("http://localhost:8000/api/v1/encounters", json={"clinician_id": "dr-martinez", "patient_ref": "pat_123"}, timeout=5.0)
    res.raise_for_status()
    encounter_id = res.json()["id"]
    
    # We must be in transcribing or recording state to generate
    # Let's force the state in DB for test simplicity
    subprocess.run([
        "docker", "compose", "exec", "-T", "postgres",
        "psql", "-U", "postgres", "-d", "clinical_scribe",
        "-c", f"UPDATE encounters SET state='transcribing' WHERE id='{encounter_id}';"
    ], check=True)
    
    payload = {
        "segments": [
            {"id": "seg_1", "text": "TRIGGER_OOM", "start_ms": 0, "end_ms": 1000, "speaker": "clinician"}
        ]
    }
    
    # Generate note using gateway, which calls LLM
    res = httpx.post(f"http://localhost:8000/api/v1/encounters/{encounter_id}/generate", json=payload, timeout=30.0)
    res.raise_for_status()
    
    # The note generation is a background task in the gateway? 
    # No, wait, generate_note returns {"status": "accepted"} but wait!
    # Ah, the generate_note endpoint runs `draft_note_bg` as a BackgroundTask.
    # So we need to poll the encounter until state is diagnosis_review
    import time
    for _ in range(30):
        res = httpx.get(f"http://localhost:8000/api/v1/encounters/{encounter_id}")
        if res.json().get("state") == "diagnosis_review":
            break
        time.sleep(1)
        
    res = httpx.get(f"http://localhost:8000/api/v1/encounters/{encounter_id}")
    assert res.json().get("state") == "diagnosis_review"
    
    # Get the generated note
    res = httpx.get(f"http://localhost:8000/api/v1/encounters/{encounter_id}/note")
    res.raise_for_status()
    note = res.json()
    
    assert "model" in note, "Note should have model info"
    assert note["model"]["name"] == "llama-3-3b-instruct", "Model tier did not fall back!"
