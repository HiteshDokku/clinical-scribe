# ADR-0009: Fix duplicate section numbering in FF-180

**Status:** accepted
**Date:** 2026-09-20
**Owner:** Krishna Patil

## Context

The submitted FF-180 form numbers both "Problem Statement" and "Project
Objectives" as section 3. Trivial, but worth fixing before the next
submission so the numbering is consistent across the synopsis and any
document that references it by section number (including this
implementation plan).

## Decision

Renumber "Project Objectives" as section 4 in the next FF-180 revision,
shifting "Proposed System Architecture" to section 5, "Key Features" to
section 6, and so on. Update any cross-references in `docs/architecture.md`
accordingly when the revised form is finalized.

## Consequences

- Removes a small but easily-noticed inconsistency from the submitted
  paperwork.

## Alternatives considered

- **Leave as-is:** rejected — costs nothing to fix and a reviewer noticing
  it reflects poorly on attention to detail elsewhere.
