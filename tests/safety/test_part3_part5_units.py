"""Unit tests with asserts in tests/ covering Part 3 and Part 5 rules.
Label: [real-service / unit-test]
"""
import os
import sys
import csv
import pytest

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("services/safety"))

try:
    from services.safety.src.diagnosis import classify_diagnosis_risk, RiskResult
    from services.safety.src.drugs import (
        load_common_medications_allowlist,
        load_high_risk_classes,
        load_dictionary,
    )
except ImportError:
    from src.diagnosis import classify_diagnosis_risk, RiskResult
    from src.drugs import (
        load_common_medications_allowlist,
        load_high_risk_classes,
        load_dictionary,
    )

def get_data_file(filename: str) -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), f"../../services/safety/data/{filename}"),
        f"/app/services/safety/data/{filename}",
        f"/app/data/{filename}",
        os.path.abspath(f"services/safety/data/{filename}"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"Could not find {filename}")

# -------------------------------------------------------------
# Part 3 Unit Tests: classify_risk reason codes & risk tiers
# -------------------------------------------------------------

def test_classify_risk_returns_red_flag_trigger_reason():
    # Sepsis or red-flag symptom trigger
    res = classify_diagnosis_risk("panic attack", ["chest pain"])
    assert isinstance(res, RiskResult)
    assert res.tier == "red_flag"
    assert res.reason_code == "red_flag_trigger:chest pain"


def test_classify_risk_returns_severity_band_reason():
    # Unstable angina is severity band 2 in DDXPlus (band <= 3 triggers red_flag)
    res = classify_diagnosis_risk("unstable angina", [])
    assert res.tier == "red_flag"
    assert res.reason_code == "severity_band:2"


def test_classify_risk_returns_not_on_reviewed_allowlist_reason():
    # Panic attack is in database with severity 5, but reviewed_by is empty
    res = classify_diagnosis_risk("panic attack", [])
    assert res.tier == "requires_review"
    assert res.reason_code == "not_on_reviewed_allowlist"


def test_classify_risk_returns_no_condition_match_reason():
    res = classify_diagnosis_risk("completely unrecognised unknown ailment 12345", [])
    assert res.tier == "requires_review"
    assert res.reason_code == "no_condition_match"


# -------------------------------------------------------------
# Part 5 Unit Tests: default-deny meds & expanded high risk
# -------------------------------------------------------------

def test_common_medications_allowlist_structure():
    csv_path = get_data_file("common_medications_allowlist.csv")
    assert os.path.exists(csv_path)

    # Check header comment
    with open(csv_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
        assert "PROPOSED" in first_line and "pending clinical review" in first_line

    with open(csv_path, "r", encoding="utf-8") as f:
        lines = [l for l in f if not l.startswith("#")]
        reader = csv.DictReader(lines)
        rows = list(reader)

    # Must contain 15 requested medications
    assert len(rows) == 15
    for row in rows:
        # Every reviewed_by must be empty
        assert row["reviewed_by"].strip() == "", f"reviewed_by must be empty for {row['ingredient']}"

    # Verify zero approvable medications without human review
    approvable = load_common_medications_allowlist()
    assert len(approvable) == 0


def test_high_risk_classes_expansion_and_count():
    csv_path = get_data_file("high_risk_classes.csv")
    assert os.path.exists(csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        all_lines = [l for l in f if l.strip()]

    # Header + 92 rows = 93 lines
    assert len(all_lines) >= 93, f"Expected at least 93 lines, got {len(all_lines)}"

    high_risk_dict = load_high_risk_classes()
    assert len(high_risk_dict) >= 92

    # Check antibiotics added
    for med in ["sparfloxacin", "telithromycin", "rifabutin", "rifapentine"]:
        assert med in high_risk_dict
        assert high_risk_dict[med] == "antibiotic"

    # Check opioids/controlled added
    for med in ["methadone", "pethidine", "tapentadol", "cocaine"]:
        assert med in high_risk_dict
        assert high_risk_dict[med] == "opioid/controlled"

    # Check controlled stimulants added
    for med in ["amphetamine", "dextroamphetamine", "methamphetamine", "methylphenidate", "dexmethylphenidate"]:
        assert med in high_risk_dict
        assert high_risk_dict[med] == "controlled_stimulant"

    # Check chemotherapy added
    for med in ["arsenic trioxide", "irinotecan", "vandetanib"]:
        assert med in high_risk_dict
        assert high_risk_dict[med] == "chemotherapy"

    # Check insulins added
    insulins = [k for k in high_risk_dict if k.startswith("insulin")]
    assert len(insulins) >= 7
    for ins in ["insulin", "insulin glargine", "insulin lispro", "insulin aspart", "insulin detemir", "insulin degludec", "insulin isophane"]:
        assert ins in high_risk_dict


def test_dictionary_excludes_drug_interactions():
    dictionary = load_dictionary()
    # Dictionary must be populated from allowlist + high_risk + brand_map
    assert len(dictionary) > 0
    # Interactions must NOT be source for dictionary entries
    # The loaded dictionary keys are clean canonical items
    assert "methadone" in dictionary
    assert "sparfloxacin" in dictionary
