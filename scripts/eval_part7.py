"""Part 7 Evaluation Script: Run real LLM 5 times on the cold fixture transcript
and report where 'not on any medication' lands each time.
"""
import json
import httpx

FIXTURE_SEGMENTS = [
    {"id": "seg_1", "text": "Good morning. What is the issue?", "start_ms": 0, "end_ms": 2000},
    {"id": "seg_2", "text": "I have been facing cold for the past few days.", "start_ms": 2000, "end_ms": 5000},
    {"id": "seg_3", "text": "Are you on any medication?", "start_ms": 5000, "end_ms": 7000},
    {"id": "seg_4", "text": "No, I'm not on any medication.", "start_ms": 7000, "end_ms": 9000},
]

LLM_URL = "http://llm:8080/extract_and_diagnose"

def run_eval():
    print("=" * 60, flush=True)
    print("PART 7 EVALUATION: 5 REAL LLM RUNS ON FIXTURE TRANSCRIPT", flush=True)
    print("=" * 60, flush=True)
    print("Fixture Transcript:", flush=True)
    for s in FIXTURE_SEGMENTS:
        print(f"  [{s['id']}] {s['text']}", flush=True)
    print("-" * 60, flush=True)

    results = []

    for run_idx in range(1, 6):
        print(f"\n>>> RUN {run_idx} / 5 starting...", flush=True)
        payload = {
            "encounter_id": f"eval_run_{run_idx}",
            "segments": FIXTURE_SEGMENTS
        }

        try:
            with httpx.Client(timeout=180.0) as client:
                resp = client.post(LLM_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            print(f"Error calling LLM on run {run_idx}: {e}", flush=True)
            results.append({"run": run_idx, "error": str(e)})
            continue

        diag = data.get("diagnosis", {})
        sections = diag.get("sections", {})
        subj = sections.get("subjective", {})
        obj = sections.get("objective", {})
        assess = sections.get("assessment", {})

        subj_stmts = subj.get("statements", [])
        obj_stmts = obj.get("statements", [])
        assess_stmts = assess.get("statements", [])

        print(f"Subjective statements ({len(subj_stmts)}):", flush=True)
        for s in subj_stmts:
            print(f"  - [{s.get('id')}] {s.get('text')} (evidence: {s.get('evidence')})", flush=True)

        print(f"Objective (insufficient_content={obj.get('insufficient_content')}, reason={obj.get('reason')}):", flush=True)
        for s in obj_stmts:
            print(f"  - [{s.get('id')}] {s.get('text')} (evidence: {s.get('evidence')})", flush=True)

        print(f"Assessment statements ({len(assess_stmts)}):", flush=True)
        for s in assess_stmts:
            print(f"  - [{s.get('id')}] {s.get('text')} (tier: {s.get('risk_tier')})", flush=True)

        # Determine where 'not on any medication' or seg_4 landed
        landing = []
        for s in subj_stmts:
            text_lower = s.get("text", "").lower()
            ev = s.get("evidence") or []
            if "medication" in text_lower or "seg_4" in ev or "med" in text_lower:
                landing.append(f"Subjective: '{s.get('text')}' (ev={ev})")

        for s in obj_stmts:
            text_lower = s.get("text", "").lower()
            ev = s.get("evidence") or []
            if "medication" in text_lower or "seg_4" in ev or "med" in text_lower:
                landing.append(f"Objective: '{s.get('text')}' (ev={ev})")

        for s in assess_stmts:
            text_lower = s.get("text", "").lower()
            ev = s.get("evidence") or []
            if "medication" in text_lower or "seg_4" in ev or "med" in text_lower:
                landing.append(f"Assessment: '{s.get('text')}' (ev={ev})")

        if not landing:
            landing_str = "Not extracted as a distinct statement"
        else:
            landing_str = "; ".join(landing)

        print(f"==> RESULT Run {run_idx}: 'not on any medication' landed in: {landing_str}", flush=True)
        print(f"==> Objective insufficient_content: {obj.get('insufficient_content')}", flush=True)

        results.append({
            "run": run_idx,
            "landing": landing_str,
            "obj_insufficient": obj.get("insufficient_content"),
            "model": data.get("model", {}).get("name")
        })

    print("\n" + "=" * 60, flush=True)
    print("SUMMARY OF 5 RUNS:", flush=True)
    for r in results:
        if "error" in r:
            print(f"Run {r['run']}: ERROR - {r['error']}", flush=True)
        else:
            print(f"Run {r['run']}: {r['landing']} (Objective insufficient={r['obj_insufficient']}) [Model: {r['model']}]", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    run_eval()
