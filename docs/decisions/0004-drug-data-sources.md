# ADR-0004: Drug interaction and ingredient data sources

**Status:** accepted
**Date:** 2026-09-20
**Owner:** Hitesh Dokku

## Context

RxNav's Drug-Drug Interaction API was discontinued on 2 Jan 2024 with no
replacement — this was a deliberate decision by NLM, not an outage.
DrugBank's Interaction Checker retires 25 Mar 2026. UMLS/RxNorm
registration is explicitly excluded from this project's plan by team
decision: approval timelines don't fit a semester schedule and add a
dependency on an external approval process outside our control.

## Decision

1. **Interaction rules:** the ONC High-Priority list (Phansalkar et al.,
   JAMIA 2012, mirrored at `dbmi-pitt/public-PDDI-analysis` on GitHub)
   plus the CredibleMeds QT/TdP list, stored as **class-based rules** with
   a local `ingredient_class` expansion table — not flattened to a fixed
   pair list, so a drug not present in the original 2012 value sets but
   belonging to a known class (e.g. a newer SSRI) is still caught.
   Extended with DDInter 2.0 (302,516 records, CC BY-NC-SA 4.0, cited per
   row) for broader pair coverage.
2. **Ingredient normalisation:** no RxNorm/RxCUI. A local
   `ingredient_dictionary` table, matched exactly first, then via
   `rapidfuzz` fuzzy matching against both generic names and the brand
   map. Below `FUZZY_MATCH_MIN_CONFIDENCE` (default 0.72), the medication
   mention is surfaced to the clinician as `needs_manual_confirmation`
   rather than silently guessed.
3. **Brand names (India):** a public Indian medicine CSV
   (e.g. `junioralive/Indian-Medicine-Dataset` on GitHub, ~254k rows, or
   an equivalent Kaggle dataset), parsed into
   `brand_map(brand, ingredient, strength)` by splitting the composition
   columns.

## Consequences

- Every interaction flag has a `source_ref` (schema-enforced, NOT NULL at
  the DB level, tested in `tests/safety/test_interaction_flags.py`).
- We do not get canonical drug identity the way an RxCUI would provide.
  Mitigated by manually reviewing the ~50–100 ingredients actually used in
  our evaluation scripts, not attempting to validate the full 250k-row
  brand catalogue.
- The fuzzy-match confidence threshold is a tuned judgment call, not a
  scientific constant — tune it against
  `tests/safety/fixtures/adversarial_pairs.csv` and report the value used.
- Report this scope honestly in the final report: "N interaction rules
  covering M ingredients within our evaluation set," not "comprehensive
  drug interaction checking."

## Alternatives considered

- **UMLS/RxNorm full local release:** rejected — explicitly excluded from
  project scope (external approval latency).
- **DrugBank academic license:** rejected — its checker is retiring March
  2026, and approval takes longer than the time available.
- **openFDA SPL labels as the primary source:** rejected as primary —
  documents one drug's label text rather than checking a pair; a drug's
  absence from that text does not mean it has been cleared.
