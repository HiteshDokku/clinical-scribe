# ADR-0005: Fixed model — Llama 3 8B Instruct

**Status:** accepted
**Date:** 2026-09-20
**Owner:** Imran Kotwal

## Context

Llama 3 8B is not the newest open-weight option available in 2026, and an
earlier draft of this plan recommended benchmarking several candidates
through a common harness rather than committing to one. The team has since
decided to continue with Llama 3 8B specifically, to keep scope bounded
given the semester timeline.

## Decision

Fix the LLM to **Llama 3 8B Instruct**, accessed through the internal
`LLMBackend` interface (`services/llm`) over an OpenAI-compatible local
endpoint — `llama.cpp` server in development, `vLLM` in production — so
the model identity remains configuration (`LLM_MODEL_NAME`,
`LLM_QUANT` env vars), not a hardcoded assumption baked into prompts or
code, even though only one model is being evaluated in this project.

Every generated note records `model.name`, `quant`, and `prompt_version`
so results remain reproducible and attributable to an exact build.

## Consequences

- Loses the comparative "we benchmarked N models" result that a bake-off
  would have produced. The report should present Llama 3 8B results
  plainly, without implying a comparison that wasn't done.
- Gains schedule certainty: no time spent standing up multiple backends or
  reconciling prompt behavior differences across models.
- Because the backend is still abstracted behind `LLMBackend`, swapping
  models later (e.g. as future work) remains a configuration change, not
  a rewrite — this optionality is kept even though it isn't exercised in
  this project's scope.

## Alternatives considered

- **Multi-model bake-off (the earlier recommendation):** not adopted, by
  explicit team decision, to keep the semester scope bounded.
- **A newer 2026 open-weight model:** not adopted for the same reason —
  team preference to continue with the already-familiar Llama 3 8B setup.
