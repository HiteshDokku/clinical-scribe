# ADR-0003: "Diagnostic copilot" is re-scoped to non-autonomous decision support

**Status:** accepted
**Date:** 2026-09-20
**Owner:** Imran Kotwal

## Context

"Real-time, evidence-based diagnostic suggestions" is language that
describes regulated clinical decision support. An undergraduate project
with no clinical validation, no regulatory review, and no ground-truth
diagnostic dataset cannot responsibly claim this, and doing so invites a
question at review that has no good answer.

## Decision

Re-scope to two concrete, bounded, non-autonomous capabilities:

1. A **differential-consideration panel**: surfaces only conditions that
   are consistent with symptoms already explicitly stated in the
   transcript, each labeled with the transcript span(s) that triggered it
   and a one-line rationale. Never ranked, never phrased as "most likely,"
   never a diagnosis.
2. **Drug-interaction and allergy flags** from the deterministic lookup in
   `services/safety` (see ADR-0004) — never from the LLM.

The LLM proposes differential *labels* grounded in stated evidence; it
never decides what is shown as a safety flag. That decision is a rule
table, always.

## Consequences

- The schema (`differential_considerations`) enforces `trigger_spans` as
  non-empty, so a differential entry with no grounding cannot exist.
- This is a defensible, honestly-scoped claim: "grounded differential
  suggestions for review," not "diagnosis."
- The report and demo should never use the words "diagnose" or
  "recommend" for this feature.

## Alternatives considered

- **Keep the original framing:** rejected outright — an unvalidated
  autonomous diagnostic claim is the single most likely thing to draw
  serious criticism at review.
- **Drop differential suggestions entirely:** considered as a fallback if
  time runs short (see the cut list in the implementation plan), but not
  adopted as the default — the grounded, bounded version is achievable
  and demonstrates the "evidence-cited" design principle well.
