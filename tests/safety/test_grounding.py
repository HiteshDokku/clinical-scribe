from services.safety.src.grounding import verify_grounding

def test_grounding_success():
    statement = "The patient was prescribed Aspirin 81mg."
    transcript_segments = [
        {"start_ms": 0, "end_ms": 2000, "text": "I will"},
        {"start_ms": 2000, "end_ms": 4000, "text": " start you on Aspirin"},
        {"start_ms": 4000, "end_ms": 6000, "text": " 81 milligrams daily."}
    ]
    evidence_spans = [(2000, 6000)] # " start you on Aspirin 81 milligrams daily."
    
    assert verify_grounding(statement, evidence_spans, transcript_segments) is True

def test_grounding_failure_hallucination():
    statement = "The patient was advised to stop taking Aspirin."
    transcript_segments = [
        {"start_ms": 0, "end_ms": 2000, "text": "I will"},
        {"start_ms": 2000, "end_ms": 4000, "text": " start you on Aspirin"},
        {"start_ms": 4000, "end_ms": 6000, "text": " 81 milligrams daily."}
    ]
    evidence_spans = [(2000, 6000)] 
    
    # Contradiction / Not Entailed
    assert verify_grounding(statement, evidence_spans, transcript_segments) is False

def test_grounding_failure_no_evidence():
    statement = "The patient has a history of diabetes."
    transcript_segments = [
        {"start_ms": 0, "end_ms": 2000, "text": "Hello,"},
        {"start_ms": 2000, "end_ms": 4000, "text": " how are you doing today?"}
    ]
    evidence_spans = [] 
    
    assert verify_grounding(statement, evidence_spans, transcript_segments) is False
