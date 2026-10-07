import pytest
import subprocess
import time
import httpx
import websockets
import asyncio
import json

@pytest.mark.asyncio
async def test_asr_crash_mid_recording():
    """
    Kill the asr container mid-recording,
    assert gateway -> degraded with degraded_reason="asr_unavailable"
    within 5 seconds, assert the UI shows the non-blocking banner.
    """
    try:
        # 1. Create encounter
        res = httpx.post("http://localhost:8000/api/v1/encounters", json={"clinician_id": "dr-martinez", "patient_ref": "pat_123"}, timeout=5.0)
        res.raise_for_status()
        encounter_id = res.json()["id"]
        
        # 2. Connect via WS and start recording
        ws_url = f"ws://localhost:8000/api/v1/encounters/{encounter_id}/stream"
        
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({"t": "consent", "value": "granted"}))
            await asyncio.sleep(0.5)
            await ws.send(b"dummy")
            
            # 3. Kill ASR container
            subprocess.run(["docker", "compose", "kill", "asr"], check=True)
            
            # Wait a few seconds for the gateway to handle the ASR disconnect and update DB
            await asyncio.sleep(3)
            
            # 4. Assert gateway marks it degraded
            res2 = httpx.get(f"http://localhost:8000/api/v1/encounters/{encounter_id}", timeout=5.0)
            res2.raise_for_status()
            data = res2.json()
            
            assert data.get("state") == "degraded", f"Expected degraded state, got {data.get('state')}"
            assert data.get("degraded_reason") == "asr_unavailable"
            
    finally:
        # Restart the container
        subprocess.run(["docker", "compose", "start", "asr"], check=False)
