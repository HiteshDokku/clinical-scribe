# ADR-0006: Hindi–English code-switching gets a dedicated, mandatory evaluation subset

**Status:** accepted
**Date:** 2026-09-20
**Owner:** Sudesh Gawade

## Context

The project's ethics section commits to validating performance across
accents and "the Hindi-English code-switching common in Indian outpatient
consultations." Off-the-shelf Whisper handles Hinglish inconsistently
(forcing one language, or transliterating unevenly). Left unmeasured, this
is exactly the kind of uneven-performance gap the ethics section promises
to check for.

## Decision

The evaluation dataset (`eval/datasets/`) is partitioned into at least
three named subsets from the start: `english`, `code_switched`, and
`medical_terms`. Every WER/CER run reports all three separately — never
only an aggregate number. At least eight of the team-recorded consultation
scripts are deliberately written with heavy Hindi-English code-switching.

Mitigation attempts, in order of effort, to try before the deadline:
initial-prompt conditioning, forcing the ASR language setting with
romanised post-processing, an Indic-adapted Whisper variant if one proves
usable within the time available. Whatever residual gap remains after
these attempts is reported as a measured finding, not hidden or excluded
from the headline numbers.

## Consequences

- The fairness claim in the report is backed by a number, not an
  assertion.
- If the gap cannot be closed in time, it becomes an honestly reported
  limitation and a "future work" item — a legitimate outcome for a
  semester project, unlike a hidden or unmeasured gap.

## Alternatives considered

- **Report only an aggregate WER:** rejected — hides exactly the
  disparity the ethics section commits to surfacing.
- **Exclude code-switched consultations from evaluation to inflate
  headline WER:** rejected outright as scientifically dishonest.
