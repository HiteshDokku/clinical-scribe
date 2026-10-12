import os
from huggingface_hub import snapshot_download
import hashlib
import json

MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"
REVISION = "5c0be3875fda05e81f3c004ed8c7c06be308de1e" # Example pinned revision
TARGET_DIR = "services/asr/models/spkrec-ecapa-voxceleb"

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

if __name__ == "__main__":
    print(f"Downloading {MODEL_ID} revision {REVISION}...")
    local_dir = snapshot_download(
        repo_id=MODEL_ID,
        revision=REVISION,
        local_dir=TARGET_DIR,
        ignore_patterns=["*.md", ".gitattributes"]
    )
    print(f"Downloaded to {local_dir}")
    
    checksums = {}
    for root, _, files in os.walk(local_dir):
        for f in files:
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, local_dir)
            checksums[rel_path] = compute_sha256(path)
            
    with open(os.path.join(TARGET_DIR, "checksums.json"), "w") as f:
        json.dump(checksums, f, indent=2)
        
    print("Checksums generated and saved.")
