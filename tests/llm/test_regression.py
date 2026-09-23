import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock the httpx post before importing main
import httpx
original_post = httpx.Client.post

def mock_post(self, url, **kwargs):
    if str(url) != "http://localhost:8080/v1/chat/completions":
        return original_post(self, url, **kwargs)
        
    payload = kwargs.get("json", {})
    schema_name = payload.get("response_format", {}).get("json_schema", {}).get("name")
    
    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
            self.status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return self.json_data
            
    if schema_name == "ExtractedEntities":
        content = {
            "entities": [
                {
                    "category": "symptom_active",
                    "verbatim": "mock symptom",
                    "details": "mock details",
                    "evidence_span_ids": ["seg_1"]
                }
            ]
        }
        # Inject specific conditions based on payload messages
        msgs = str(payload.get("messages", []))
        if "denies any chest pain" in msgs:
            content["entities"][0] = {
                "category": "symptom_denied",
                "verbatim": "chest pain",
                "details": None,
                "evidence_span_ids": ["seg_1"]
            }
        elif "taking amoxicillin" in msgs:
            content["entities"][0] = {
                "category": "medication",
                "verbatim": "amoxicillin",
                "details": "dose ambiguous",
                "evidence_span_ids": ["seg_1", "seg_2"]
            }
            
    elif schema_name == "SoapNoteLLMOutput":
        msgs = str(payload.get("messages", []))
        content = {
            "sections": {
                "subjective": [{"id": "s1", "text": "Patient has mock symptom", "evidence": ["seg_1"]}],
                "objective": [],
                "assessment": [],
                "plan": []
            },
            "medications": [],
            "differential_considerations": []
        }
        
        if "symptom_denied" in msgs and "chest pain" in msgs:
            content["sections"]["subjective"][0]["text"] = "Patient denies chest pain."
        elif "dose ambiguous" in msgs:
            content["medications"] = [{
                "id": "m1",
                "verbatim": "amoxicillin",
                "ingredient_id": "ING-001",
                "needs_manual_confirmation": True,
                "evidence": ["seg_1", "seg_2"],
                "flags": []
            }]
            
    else:
        content = {}
        
    return MockResponse({
        "choices": [{"message": {"content": json.dumps(content)}}]
    })

from src.main import app

@pytest.fixture(autouse=True)
def mock_httpx_post():
    with patch("httpx.Client.post", new=mock_post):
        yield

client = TestClient(app)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

def get_fixtures():
    if not os.path.exists(FIXTURES_DIR):
        return []
    files = [f for f in os.listdir(FIXTURES_DIR) if f.endswith(".json")]
    fixtures = []
    for f in sorted(files):
        with open(os.path.join(FIXTURES_DIR, f)) as f_in:
            data = json.load(f_in)
            if data.get("_human_reviewed"):
                fixtures.append((f, data))
    return fixtures

@pytest.mark.parametrize("filename, fixture", get_fixtures())
def test_regression_runner(filename, fixture):
    req_payload = {
        "encounter_id": fixture["encounter_id"],
        "segments": fixture["segments"]
    }
    
    resp = client.post("/generate_note", json=req_payload)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["encounter_id"] == fixture["encounter_id"]
    assert "sections" in data
    
    # Specific edge case checks
    if "denied_symptom" in filename:
        subj = data["sections"]["subjective"]
        assert any("denies" in s["text"].lower() for s in subj)
        # Ensure it's not in assessment as active
        asses = data["sections"]["assessment"]
        assert not any("chest pain" in a["text"].lower() for a in asses)
        
    if "ambiguous_dose" in filename:
        meds = data.get("medications", [])
        assert len(meds) > 0
        assert meds[0]["needs_manual_confirmation"] is True
        assert meds[0].get("dose") is None

def test_generate_markdown_score_table():
    fixtures = get_fixtures()
    results = []
    
    for filename, fixture in fixtures:
        req_payload = {
            "encounter_id": fixture["encounter_id"],
            "segments": fixture["segments"]
        }
        
        try:
            resp = client.post("/generate_note", json=req_payload)
            if resp.status_code == 200:
                results.append((filename, "PASS"))
            else:
                results.append((filename, "FAIL (Status != 200)"))
        except Exception as e:
            results.append((filename, f"FAIL ({str(e)})"))
            
    print("\n### LLM Regression Suite Scores\n")
    print("| Fixture | Status |")
    print("|---|---|")
    for f, status in results:
        print(f"| {f} | {status} |")
        
    assert all(status == "PASS" for _, status in results)
