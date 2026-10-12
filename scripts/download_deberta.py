import os
from huggingface_hub import snapshot_download
import hashlib
import json

MODEL_ID = "cross-encoder/nli-deberta-v3-small"
REVISION = "fa2804872c3b4bd748f38c0185cc85775361e735"
TARGET_DIR = "services/safety/models/nli-deberta-v3-small"

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
