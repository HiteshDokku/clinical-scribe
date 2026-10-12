# ADR-0015: Speaker embedding model — build-time downloads are not runtime egress

**Status:** accepted · supersedes ADR-0013
**Date:** 2026-10-08
**Owner:** team

## Context
ADR-0013 rejected pyannote because its weights are gated behind a one-time
Hugging Face token, treating this as an air-gap violation. That conflates a
one-time, human-performed weight download with runtime egress of patient
data, which is what ADR-0001 actually restricts.

## Decision
Model weights may be downloaded once, at build time, on a networked machine
by a human, with the revision pinned and checksums committed. Containers
load them from a local path with HF_HUB_OFFLINE=1. No token or network
access exists at runtime. Speaker embeddings use
speechbrain/spkrec-ecapa-voxceleb (Apache-2.0, ungated) with the
two-centroid online assignment from the diarization spec.

## Consequences
pyannote is not ruled out in principle, only not needed unless ECAPA fails
the 90% turn-level accuracy bar.