# AGENTS.md — standing instructions for any coding agent working in this repo

## What this project is

A local-first clinical scribe. Patient audio and clinical text must never
leave the machine. This constraint outranks every other consideration,
including convenience, performance, and your own suggestions. If a task
seems to require violating it, stop and ask rather than finding a
workaround.

## Absolute prohibitions

- Never add a dependency that calls a hosted AI, speech, or analytics API.
  Banned: `openai`, `anthropic`, `google-generativeai`, `boto3`, `azure-*`,
  `assemblyai`, `deepgram`, `sentry-sdk`, any telemetry-by-default package.
- Never write audio to disk, `/tmp`, or any mounted volume. RAM only.
- Never log, print, or trace clinical text, patient identifiers, or raw
  transcripts. Redact before logging, always.
- Never add an "approve all" or "auto-submit" action to the review UI.
- Never invent clinical content. Every generated statement needs a
  non-empty evidence array pointing at real transcript span ids.
- Never treat drug-interaction checking as an LLM task. It is a
  deterministic table lookup against `services/safety`'s local dictionary.
  Every row in `drug_interactions` needs a non-null `source_ref`.
- Never modify `packages/contracts/` without an explicit instruction that
  names the schema change and points to the ADR that authorizes it.
- Never edit files under `eval/datasets/` or `docs/decisions/` — these are
  human-owned.
- Never call out to RxNorm/RxNav, UMLS, or any other external terminology
  service at runtime. Ingredient normalisation is local-dictionary +
  fuzzy-match only (see ADR-0004).

## Stack (do not substitute without asking)

Python 3.12 · FastAPI · Pydantic v2 · pytest · uv for dependency management.
React 19 + TypeScript + Vite + Tailwind. PostgreSQL 16 · Redis 7.
Docker Compose. Llama 3 8B Instruct (fixed, see ADR-0005) via an
OpenAI-compatible local endpoint (llama.cpp dev / vLLM prod).

## Definition of done for any task

1. Type checks pass (`mypy` / `tsc`) and `ruff`/`eslint` are clean.
2. Unit tests written and passing; an integration test if the change
   crosses a service boundary.
3. `make verify-offline` still passes.
4. For UI work: browser-verified, with a screenshot attached to the task
   artifact.
5. A one-paragraph summary of what changed and why.

## House style

Small functions. Explicit types at every service boundary. No clever
metaprogramming. Comments explain *why*, never *what*. If a requirement
seems contradictory or ambiguous, stop and ask rather than guessing —
this is a safety-relevant medical system, not a prototype where a wrong
guess is cheap.
