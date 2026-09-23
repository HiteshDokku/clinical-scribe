# ADR-0008: Energy-per-consultation is measured, not left as "to be confirmed"

**Status:** accepted
**Date:** 2026-09-20
**Owner:** Imran Kotwal

## Context

The FF-180's environment table leaves per-consultation inference energy as
"to be confirmed with on-device power measurement once a prototype is
running." That prototype now exists in this plan's milestones (M2–M4), so
the placeholder should be replaced with an actual measurement method and,
eventually, a number.

## Decision

Sample GPU power draw at 200ms intervals for the duration of a full
consultation using `nvidia-smi --query-gpu=power.draw --format=csv -lms
200`, integrate over time to get energy, subtract an idle-GPU baseline
measured separately, and divide by the number of consultations processed
in the sampling window. Report the result in kWh per consultation, with
the measurement method stated alongside the number — never a bare figure
with no methodology.

When comparing against the cloud-hosted benchmark already cited in the
synopsis's environment section, state explicitly that this project's
number is a device-level measurement and the cited figure is a
datacentre-level one — different measurement boundaries, disclosed rather
than conflated.

## Consequences

- Fills the blank cell in the environment table with a defensible,
  reproducible number instead of a placeholder.
- `tests/eval/test_harness_reproducibility.py` includes a smoke test that
  the energy script produces a nonzero value when a GPU is present, and
  skips cleanly (not silently) when it isn't.

## Alternatives considered

- **Leave it as "to be confirmed" in the final report:** rejected — the
  measurement is inexpensive to perform (a short script) and its absence
  weakens an otherwise well-argued sustainability section.
