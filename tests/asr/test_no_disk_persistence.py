import os
import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from src.main import app

def get_inodes(paths):
    inodes = set()
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            for entry in os.scandir(path):
                inodes.add(entry.inode())
        except PermissionError:
            pass
    return inodes

def test_no_disk_persistence(fixture_wav_bytes):
    paths_to_watch = ["/tmp", "/var/tmp", str(Path.cwd())]
    
    inodes_before = get_inodes(paths_to_watch)
    
    client = TestClient(app)
    with client.websocket_connect("/transcribe") as websocket:
        websocket.send_text(json.dumps({"encounter_id": "test-123"}))
        websocket.send_bytes(fixture_wav_bytes)
        
        try:
            # We don't care about the events for the persistence test.
            # Just give it a small moment to process and then we exit the context block, which closes the socket.
            # To ensure it processes, we can wait for 1 event if we know one is coming, or just close.
            import time
            time.sleep(2)  # Give the server time to process the chunks
        except Exception:
            pass

    inodes_after = get_inodes(paths_to_watch)
    
    new_inodes = inodes_after - inodes_before
    assert len(new_inodes) == 0, f"New files created on disk: {new_inodes}"
