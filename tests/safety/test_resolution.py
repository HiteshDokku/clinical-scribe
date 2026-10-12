try:
    from src.drugs import resolve_medication, get_high_risk_class
except ModuleNotFoundError:
    from services.safety.src.drugs import resolve_medication, get_high_risk_class


def _classify_resolution(med: str) -> tuple[str, str]:
    ingredients = resolve_medication(med)
    res = ingredients[0] if ingredients else "UNRESOLVED:missing"
    if res.startswith("UNRESOLVED:"):
        reason = "unresolved"
    else:
        hr_class = get_high_risk_class(res)
        if hr_class and hr_class != "UNKNOWN_MANUAL_CONFIRMATION_REQUIRED":
            reason = f"high_risk_class={hr_class}"
        else:
            reason = "exact match, not high-risk"
    return res, reason

def test_resolution_amoxicillin():
    res, reason = _classify_resolution("amoxicillin")
    print(f"\namoxicillin -> {reason} ({res})")
    assert reason == "high_risk_class=antibiotic"
    assert res == "amoxicillin"

def test_resolution_amoxycillin():
    res, reason = _classify_resolution("amoxycillin")
    print(f"\namoxycillin -> {reason} ({res})")
    assert reason == "unresolved"
    assert res.startswith("UNRESOLVED:")

def test_resolution_augmentin_625():
    res, reason = _classify_resolution("Augmentin 625")
    print(f"\nAugmentin 625 -> {reason} ({res})")
    assert reason == "high_risk_class=antibiotic"
    assert res == "amoxicillin"

def test_resolution_dolo_650():
    res, reason = _classify_resolution("Dolo 650")
    print(f"\nDolo 650 -> {reason} ({res})")
    assert reason == "exact match, not high-risk"
    assert res == "paracetamol"

def test_resolution_xyzzyplex():
    res, reason = _classify_resolution("xyzzyplex")
    print(f"\nxyzzyplex -> {reason} ({res})")
    assert reason == "unresolved"
    assert res == "UNRESOLVED:xyzzyplex"

def test_resolution_ibuprofen():
    res, reason = _classify_resolution("ibuprofen")
    print(f"\nibuprofen -> {reason} ({res})")
    assert reason == "unresolved"
    assert res == "UNRESOLVED:ibuprofen"

def test_resolution_warfarin():
    res, reason = _classify_resolution("warfarin")
    print(f"\nwarfarin -> {reason} ({res})")
    assert reason == "high_risk_class=anticoagulant"
    assert res == "warfarin"

def test_resolution_tramadol():
    res, reason = _classify_resolution("tramadol")
    print(f"\ntramadol -> {reason} ({res})")
    assert reason == "high_risk_class=opioid"
    assert res == "tramadol"
