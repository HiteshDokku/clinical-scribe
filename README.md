# Privacy-Preserving Clinical Scribe and Diagnostic Copilot


A fully local pipeline that turns a recorded doctor-patient consultation into
a structured, evidence-cited SOAP note and a safety-checked draft
prescription — with no patient audio or clinical text ever leaving the
machine.

## Why this exists

Cloud-hosted ambient scribes are effective but transmit PHI to third-party
APIs, which conflicts with HIPAA/DPDP in regulated settings. This project
builds and evaluates a single local-first pipeline: transcription, note
generation, and prescription drafting, under one privacy-hardened
architecture. See `docs/architecture.md` for the full design and
`docs/decisions/` for the reasoning behind every non-obvious choice.

## Quickstart

```bash
cp .env.example .env
make dev              # builds and starts all six services + Postgres + Redis
make test             # unit + integration tests
make verify-offline   # asserts zero outbound egress except the FHIR allowlist
make eval DATASET=eval/datasets/pilot.yaml
```

Open `http://localhost:5173` for the consultation UI.

## What "local-first" actually means here

- No service in this stack has a network path to the public internet except
  the FHIR gateway, which is restricted to one allowlisted host:port.
- Audio never touches disk. It lives in a bounded RAM ring buffer and is
  zeroed at session end.
- Transcripts are held in Redis with a TTL and are not retained unless the
  clinician opts in per encounter.
- Every clinical statement in a generated note carries the transcript spans
  that support it. Statements with no support cannot be produced — the
  schema does not permit it.
- The audit log (`audit_log` table) is append-only at the database
  permission level, not just by convention.

Full threat model and controls: `docs/architecture.md §8`.

## Repository map

| Path | What's here |
|---|---|
| `services/gateway` | Orchestration, state machine, auth, audit |
| `services/asr` | Streaming local speech-to-text |
| `services/llm` | Local Llama 3 8B Instruct, constrained note generation |
| `services/safety` | Deterministic drug-interaction and grounding checks |
| `services/fhir-gateway` | The only component allowed to reach outside the LAN |
| `apps/web` | Clinician-facing consultation and review UI |
| `eval/` | The metrics harness — this is a first-class part of the project, not an afterthought |
| `docs/decisions/` | ADRs — read these before changing architecture |


## Status

See `docs/review-1/` and `docs/review-2/` for milestone evidence exported
from Antigravity (implementation plans, test results, screenshots).
