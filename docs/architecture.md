# Architecture — Privacy-Preserving Clinical Scribe

> This document is the authoritative design reference for the project.
> All ADRs in `docs/decisions/` are subordinate to this document.
> Sections §1–§2 and §4–§8 are stubs to be filled in at each milestone.

---

## §1 — Problem Statement

*(To be filled in at M1.)*

---

## §2 — High-Level Design

*(To be filled in at M1.)*

---

## §3 — Repo Layout

```
clinical-scribe/
├── services/                  # Backend Python microservices (FastAPI, uv)
│   ├── gateway/               # Orchestration, state machine, auth, audit log
│   │   ├── src/main.py        # FastAPI app — GET /healthz, future: encounter API
│   │   ├── pyproject.toml     # uv-managed deps; ruff + mypy strict configured
│   │   └── Dockerfile         # python:3.12-slim; port 8000
│   ├── asr/                   # Streaming local speech-to-text (faster-whisper)
│   │   ├── src/main.py        # FastAPI app — GET /healthz, future: /transcribe WS
│   │   ├── pyproject.toml
│   │   └── Dockerfile         # python:3.12-slim; port 8001
│   ├── llm/                   # Local Llama 3 8B Instruct, note generation
│   │   ├── src/main.py        # FastAPI app — GET /healthz, future: /extract /compose
│   │   ├── prompts/           # System + user prompt templates (Jinja2)
│   │   ├── pyproject.toml
│   │   └── Dockerfile         # python:3.12-slim; port 8080
│   ├── safety/                # Deterministic drug-interaction + grounding checks
│   │   ├── src/main.py        # FastAPI app — GET /healthz, future: /check
│   │   ├── pyproject.toml
│   │   └── Dockerfile         # python:3.12-slim; port 8002
│   └── fhir-gateway/          # The ONLY component allowed external egress
│       ├── src/main.py        # FastAPI app — GET /healthz, future: /push /pull
│       ├── pyproject.toml
│       └── Dockerfile         # python:3.12-slim; port 8003
│
├── apps/
│   └── web/                   # Clinician-facing UI (React 19 + Vite + Tailwind)
│       ├── src/               # React components, hooks, pages
│       ├── Dockerfile         # nginx:alpine static build for compose
│       └── package.json       # (added at M2)
│
├── packages/
│   └── contracts/             # Shared Pydantic v2 schemas — DO NOT edit without ADR
│
├── tests/                     # All integration + security tests (pytest)
│   ├── conftest.py            # Shared fixtures (pg_conn, sample_encounter_id)
│   ├── security/              # CI-enforced policy tests — run on every push
│   │   ├── test_no_cloud_deps.py   # Bans openai/anthropic/etc. in pyproject.toml
│   │   ├── test_no_egress.py       # Verifies containers can't reach public internet
│   │   └── test_audit_immutable.py # Verifies audit_log is append-only at DB level
│   ├── gateway/               # Gateway integration tests
│   ├── asr/                   # ASR integration tests
│   ├── llm/                   # LLM integration tests
│   ├── safety/                # Safety service tests
│   ├── fhir/                  # FHIR gateway tests (egress allowlist guard)
│   ├── contracts/             # Schema compatibility tests
│   ├── chaos/                 # Resilience / fault-injection tests
│   └── fairness/              # Hinglish + dialect equity tests (ADR-0006)
│
├── eval/                      # Metrics harness — first-class, not an afterthought
│   ├── datasets/              # Human-owned evaluation datasets (do not edit)
│   │   └── drugs/             # Local drug dictionary (ingredient_dictionary.csv, brand_map.csv)
│   └── ...
│
├── infra/
│   ├── db/init/               # Postgres initialisation SQL (run once by postgres container)
│   ├── scripts/               # Helper scripts (wait-for-healthy.sh, build-llamacpp.sh, etc.)
│   ├── secrets/               # Placeholder dir — real certs injected in prod via CI secrets
│   ├── firewall/              # nftables / iptables rules enforcing ADR-0001
│   └── observability/         # OTel collector config
│
├── docs/
│   ├── architecture.md        # ← This file
│   └── decisions/             # ADRs (human-owned — do not edit files here)
│
├── docker-compose.yml         # Dev stack; all services on "clinic" internal bridge network
├── docker-compose.prod.yml    # Production overrides
├── .env.example               # Env template — copy to .env before running
├── Makefile                   # Convenience targets: dev, test, verify-offline, eval
├── AGENTS.md                  # Standing instructions for coding agents
└── README.md
```

### Network topology

```
                     ┌──────────────────────────────────────────┐
                     │  Docker network: "clinic"  (internal:true) │
                     │                                            │
                     │   postgres ◄──── gateway                  │
                     │   redis    ◄──── gateway                  │
                     │   asr      ◄──── gateway                  │
                     │   llm      ◄──── gateway                  │
                     │   safety   ◄──── gateway                  │
                     │   fhir-gateway ◄─ gateway                 │
                     └──────────┬───────────────────┬────────────┘
                                │ gateway            │ fhir-gateway
                     ┌──────────▼───────────────────▼────────────┐
                     │  Docker network: "edge"   (internal:false) │
                     │                                            │
                     │   web ──────────────────────────           │
                     │   (port 5173 published)                    │
                     │   gateway (port 8000 published)            │
                     └──────────────────────────────────────────┘
                                         │
                              Public internet / LAN
                              (fhir-gateway only; allowlisted host:port)
```

### Service ports (internal)

| Service      | Port | Protocol |
|---|---|---|
| gateway      | 8000 | HTTP |
| asr          | 8001 | HTTP / WebSocket |
| safety       | 8002 | HTTP |
| fhir-gateway | 8003 | HTTP |
| llm          | 8080 | HTTP |
| web          | 5173 | HTTP (nginx) |

### Published ports (host → container)

| Env var        | Default | Container |
|---|---|---|
| `GATEWAY_PORT` | 8000    | gateway:8000 |
| `WEB_PORT`     | 5173    | web:5173 |

---

## §4 — Data Flow

*(To be filled in at M1.)*

---

## §5 — State Machine

*(To be filled in at M1.)*

---

## §6 — Audio Pipeline

*(To be filled in at M2 — ASR milestone.)*

---

## §7 — LLM Integration

*(To be filled in at M3 — LLM milestone.)*
See ADR-0005 for model selection rationale.

---

## §8 — Threat Model & Security Controls

*(To be filled in at M4 — Security review milestone.)*
See ADR-0001 (egress policy), ADR-0002 (retention tiers), ADR-0007 (hallucination definition).
