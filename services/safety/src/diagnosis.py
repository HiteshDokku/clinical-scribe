import os
import csv
from rapidfuzz import process, fuzz

def load_red_flags():
    flags = []
    path = os.path.join(os.path.dirname(__file__), "..", "data", "red_flag_triggers.csv")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                flags.append(row["symptom"].lower())
    return flags

def load_tiers():
    tiers = {}
    path = os.path.join(os.path.dirname(__file__), "..", "data", "diagnosis_risk_tiers.csv")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cond = row["condition_name"].lower()
                try:
                    tiers[cond] = int(row["severity"])
                except ValueError:
                    pass
    return tiers

def load_common_allowlist():
    allowed = set()
    path = os.path.join(os.path.dirname(__file__), "..", "data", "common_allowlist.csv")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("reviewed_by", "").strip():
                    allowed.add(row["condition_name"].lower())
    return allowed

def load_aliases():
    aliases = {}
    path = os.path.join(os.path.dirname(__file__), "..", "data", "diagnosis_aliases.csv")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                aliases[row["alias"].lower()] = row["canonical_name"].lower()
    return aliases

RED_FLAGS = load_red_flags()
TIERS = load_tiers()
COMMON_ALLOWLIST = load_common_allowlist()
ALIASES = load_aliases()

class RiskResult(str):
    def __new__(cls, tier: str, reason: str):
        obj = str.__new__(cls, tier)
        obj.tier = tier
        obj.reason = reason
        obj.reason_code = reason
        return obj

    def __iter__(self):
        yield self.tier
        yield self.reason


def classify_diagnosis_risk(proposed_condition: str, symptoms: list[str]) -> RiskResult:
    """
    Deterministic risk classification.
    Returns RiskResult (subclasses str for backward-compat string equality and tuple unpacking).
    Reason codes:
      - red_flag_trigger:<name>
      - severity_band:<n>
      - not_on_reviewed_allowlist
      - no_condition_match
    """
    lower_cond = (proposed_condition or "").lower().strip()
    lower_symps = [(s or "").lower().strip() for s in symptoms]
    
    # Check red flags on condition name
    for flag in RED_FLAGS:
        if flag in lower_cond:
            return RiskResult("red_flag", f"red_flag_trigger:{flag}")
            
    # Check red flags on symptoms
    for flag in RED_FLAGS:
        for symp in lower_symps:
            if flag in symp:
                return RiskResult("red_flag", f"red_flag_trigger:{flag}")
                
    # Normalize condition via aliases
    if lower_cond in ALIASES:
        lower_cond = ALIASES[lower_cond]
        
    # Match condition
    choices = list(TIERS.keys())
    matched_cond = None
    if choices:
        match = process.extractOne(lower_cond, choices, scorer=fuzz.WRatio)
        if match and match[1] >= 90.0:
            matched_cond = match[0]
            
    if not matched_cond:
        return RiskResult("requires_review", "no_condition_match")
        
    severity = TIERS.get(matched_cond, 3)
    
    # MOST severe band (severity 1 or 2)
    if severity <= 2:
        return RiskResult("red_flag", f"severity_band:{severity}")
        
    # LEAST severe band (severity 4 or 5)
    if severity >= 4:
        if matched_cond in COMMON_ALLOWLIST:
            return RiskResult("common", f"severity_band:{severity}")
        else:
            return RiskResult("requires_review", "not_on_reviewed_allowlist")
            
    # Everything else (e.g. severity 3)
    return RiskResult("requires_review", f"severity_band:{severity}")

