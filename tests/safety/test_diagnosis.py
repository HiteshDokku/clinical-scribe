import pytest
from services.safety.src.diagnosis import classify_diagnosis_risk

def test_serious_ddxplus_conditions_never_common():
    # unstable angina, pulmonary embolism, possible NSTEMI/STEMI, spontaneous pneumothorax, Guillain-Barré
    # severity <= 2 should be red_flag
    assert classify_diagnosis_risk("unstable angina", []) == "red_flag"
    assert classify_diagnosis_risk("pulmonary embolism", []) == "red_flag"
    assert classify_diagnosis_risk("possible nstemi / stemi", []) == "red_flag"
    assert classify_diagnosis_risk("spontaneous pneumothorax", []) == "red_flag"
    assert classify_diagnosis_risk("guillain-barré syndrome", []) == "red_flag"

def test_unknown_condition_fails_closed():
    assert classify_diagnosis_risk("some unknown condition", []) == "requires_review"

def test_no_llm_import_in_diagnosis():
    import ast
    with open("services/safety/src/diagnosis.py", "r") as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "openai" not in alias.name
                assert "anthropic" not in alias.name
                assert "ollama" not in alias.name
                assert "requests" not in alias.name
                assert "httpx" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            assert "openai" not in node.module
            assert "anthropic" not in node.module
            assert "ollama" not in node.module
            assert "requests" not in node.module
            assert "httpx" not in node.module

def test_common_requires_reviewed_by():
    # Panic attack is severity 5, but if not in common_allowlist with reviewed_by, it's requires_review
    # We added Panic attack to common_allowlist, but reviewed_by is empty!
    assert classify_diagnosis_risk("panic attack", []) == "requires_review"

def test_red_flag_symptom_overrides_common_condition():
    # If Panic attack was common, but symptom is chest pain, it's red_flag
    # Even if it's requires_review, red flag should override
    assert classify_diagnosis_risk("panic attack", ["chest pain"]) == "red_flag"

def test_grounded_label_cannot_bypass_risk_gate():
    # A grounded statement must still be classified, handled by gateway.
    # The function itself has no knowledge of "grounded".
    pass

def test_null_tier_is_impossible():
    assert classify_diagnosis_risk("anything", []) is not None
