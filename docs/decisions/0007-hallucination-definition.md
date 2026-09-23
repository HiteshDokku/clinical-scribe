# ADR-0007: Hallucination is measured, not quoted from industry averages

**Status:** accepted
**Date:** 2026-09-20
**Owner:** Imran Kotwal

## Context

The original synopsis cites an industry-average ambient-scribe
hallucination rate (~7%) as if it were a property of this system. It is
not — it describes other, cloud-hosted products. The safety section needs
its own measured number.

## Decision

Define, precisely, and measure:

- **Unsupported-claim rate** = (unsupported + contradicted statements) ÷
  total statements, where a rater marks each atomic clinical statement in
  a generated note as `supported` (its cited evidence spans entail it),
  `unsupported` (nothing in the transcript entails it), or `contradicted`.
  Reported per SOAP section.
- **Omission rate** = clinically relevant facts present in the transcript
  but absent from the note. Measured separately, since omission is
  arguably the more dangerous failure mode and is easy to forget to check.

The externally cited ~7% figure is retained only as a comparison point,
properly attributed, in the literature review — never presented as this
system's own result.

## Consequences

- The safety section's headline claim is reproducible from
  `eval/harness/` against committed fixtures, not borrowed.
- Per-section breakdown will very likely show Assessment and Objective as
  the worst sections, consistent with the published finding about
  physical-examination content — report this, don't be surprised by it.

## Alternatives considered

- **Keep quoting the industry figure as this system's number:** rejected
  — factually wrong and undermines the credibility of the whole safety
  section if noticed.
