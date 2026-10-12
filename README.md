<h1 align="center">Clinical Scribe — Privacy-Preserving AI Scribe & Diagnostic Copilot</h1>

<p align="center">
  <b>Listens locally. Drafts with evidence. Gates every claim. The clinician signs. Patient data never leaves the machine.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54&labelColor=555555" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white&labelColor=555555" alt="FastAPI">
  <img src="https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white&labelColor=555555" alt="Pydantic">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=white&labelColor=555555" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white&labelColor=555555" alt="TypeScript">
  <img src="https://img.shields.io/badge/Vite-6-646CFF?style=for-the-badge&logo=vite&logoColor=white&labelColor=555555" alt="Vite">
  <img src="https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white&labelColor=555555" alt="Tailwind CSS">
</p>
<p align="center">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white&labelColor=555555" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white&labelColor=555555" alt="Redis">
  <img src="https://img.shields.io/badge/Llama_3-8B_Instruct-0467DF?style=for-the-badge&logo=meta&logoColor=white&labelColor=555555" alt="Llama 3 8B">
  <img src="https://img.shields.io/badge/Ollama-Local-000000?style=for-the-badge&logo=ollama&logoColor=white&labelColor=555555" alt="Ollama">
  <img src="https://img.shields.io/badge/faster--whisper-CTranslate2-FF6F00?style=for-the-badge&logo=openai&logoColor=white&labelColor=555555" alt="faster-whisper">
  <img src="https://img.shields.io/badge/HL7-FHIR-E8412C?style=for-the-badge&logo=hl7&logoColor=white&labelColor=555555" alt="HL7 FHIR">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white&labelColor=555555" alt="Docker Compose">
</p>

---

## Table of Contents

- [Core Concept](#core-concept)
- [Non-Negotiable Safety Principles](#non-negotiable-safety-principles)
- [Architecture](#architecture)
- [Encounter Lifecycle](#encounter-lifecycle)
- [Live Audio Pipeline](#live-audio-pipeline)
- [Two-Phase Note Generation](#two-phase-note-generation)
- [Safety Layer](#safety-layer)
- [Clinician Review & Sign-off](#clinician-review--sign-off)
- [EHR Integration (FHIR)](#ehr-integration-fhir)
- [Data Model & Auditability](#data-model--auditability)
- [Privacy & Security Controls](#privacy--security-controls)
- [Testing & Evaluation](#testing--evaluation)
- [Architecture Decision Records](#architecture-decision-records)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Contributing](#contributing)

---

## Core Concept

Clinical Scribe turns a recorded doctor–patient consultation into a **structured SOAP note** and a **draft prescription**. Every statement cites the transcript segments it came from. A deterministic safety layer checks every claim, and nothing is final until a clinician reviews and signs it.

The AI only **drafts**. Deterministic code does the **gating**. The clinician **decides**.

```mermaid
flowchart TD
    A["Consent captured<br/>verbal or written"] --> B["Live audio stream<br/>RAM only"]
    B --> C["Local ASR + diarization<br/>faster-whisper + ECAPA"]
    C --> D["Timestamped transcript segments"]
    D --> E["Local LLM extraction<br/>clinical entities + evidence ids"]
    E --> F["Draft S / O / A<br/>every statement cites segments"]
    F --> G{"Deterministic safety gate<br/>risk tier · grounding"}
    G -->|"red_flag / requires_review"| H["Clinician writes own determination"]
    G -->|"common + allowlisted"| I["Clinician confirms diagnosis"]
    H --> I
    I --> J["Local LLM drafts Plan + medications"]
    J --> K{"Drug safety gate<br/>resolution · high-risk class · interactions"}
    K --> L["Clinician confirms meds + acknowledges flags"]
    L --> M["Sign-off<br/>server re-validates everything"]
    M --> N["Immutable audit log + versioned note"]
    M --> O["FHIR push via the only egress service"]
```

---

## Non-Negotiable Safety Principles

These rules come from [`AGENTS.md`](AGENTS.md) and the ADRs. They take priority over convenience and performance.

| Principle | How it is enforced |
|---|---|
| **No patient data leaves the machine** | Every clinical service runs on an `internal: true` Docker network with no route out. No hosted AI, speech, or telemetry SDKs (`tests/security/test_no_cloud_deps.py`). |
| **Audio is never persisted** | Audio stays in RAM buffers only. Redis runs with `--save "" --appendonly no`. The prod ASR container is `read_only` with a `noexec` tmpfs. |
| **No invented clinical content** | Every AI statement needs a non-empty `evidence` array of real transcript segment ids. Invalid citations trigger a regeneration and are marked `ungrounded`. |
| **Drug interactions are not an LLM task** | Interactions come from a lookup in a local, cited table. Rows without a `source_ref` are dropped at load time. |
| **No "approve all" action** | Each flagged statement and medication needs its own clinician action. The server re-checks everything at sign-off. |
| **No external terminology services** | Ingredient normalisation uses a local dictionary plus fuzzy matching only. No RxNav or UMLS calls at runtime (ADR-0004). |
| **Logs never contain clinical text** | Services log structure (counts, ids) and not content. `REDACT_CLINICAL_TEXT_IN_LOGS=true` is enforced by a CI test. |

---

## Architecture

The system is a set of small FastAPI microservices behind one orchestrating **gateway**. Two Docker networks split the system into an isolated clinical zone and an edge zone.

```mermaid
flowchart LR
    subgraph EDGE["edge network · internal: false"]
        WEB["web<br/>React 19 + nginx<br/>:5173"]
        HAPI["hapi-fhir<br/>dev EHR target<br/>:8080"]
    end

    subgraph CLINIC["clinic network · internal: true · no egress"]
        GW["gateway<br/>orchestration · auth · state machine · audit<br/>:8000"]
        ASR["asr<br/>VAD · faster-whisper · ECAPA diarization<br/>:8001"]
        LLM["llm<br/>prompting · structured output · grounding<br/>:8080"]
        OLL["ollama<br/>Llama 3 8B Instruct · GPU"]
        SAF["safety<br/>risk tiers · drug resolution · interactions · NLI<br/>:8002"]
        PG[("postgres 16<br/>encounters · note_versions · audit_log")]
        RD[("redis 7<br/>ephemeral transcript · TTL · no persistence")]
        FHIR["fhir-gateway<br/>ONLY egress · allowlist + mTLS<br/>:8003"]
    end

    WEB -- "REST + WebSocket /api" --> GW
    GW -- "WS /transcribe" --> ASR
    GW -- "/extract_and_diagnose · /prescribe" --> LLM
    LLM -- "OpenAI-compatible API" --> OLL
    GW -- "/api/v1/safety/*" --> SAF
    GW --> PG
    GW --> RD
    GW -- "background push" --> FHIR
    FHIR -- "allowlisted host:port" --> HAPI
```

| Service | Port | Responsibility |
|---|---|---|
| `gateway` | 8000 | Public API, JWT + CSRF auth, Postgres RLS identity, encounter state machine, LLM/safety orchestration, audit logging, WebSocket relay to ASR |
| `asr` | 8001 | Streaming speech-to-text: Silero VAD, utterance segmentation, faster-whisper (int8, CPU), ECAPA-TDNN speaker diarization |
| `llm` | 8080 | Jinja2 prompt templates, JSON-schema structured output, evidence-id validation with retry, model fallback |
| `ollama` | 11434 | Local LLM runtime (OpenAI-compatible endpoint), GPU-reserved |
| `safety` | 8002 | Deterministic diagnosis risk tiers, medication resolution, high-risk class detection, interaction lookup, DeBERTa NLI grounding check |
| `fhir-gateway` | 8003 | Builds and validates a FHIR transaction Bundle and pushes it **only** to the allowlisted EHR host |
| `postgres` | 5432 | System of record: encounters, versioned notes, append-only audit log, users/roles |
| `redis` | 6379 | Short-lived transcript, entities, and id-map cache (TTL, persistence disabled) |
| `web` | 5173 | Clinician UI: consent gate, live transcript, staged SOAP review, audit dashboard |

---

## Encounter Lifecycle

Each encounter moves through a strict, audited state machine. Every transition writes a `state_change` row to the append-only audit log.

```mermaid
stateDiagram-v2
    [*] --> created: POST /encounters
    created --> consented: consent granted
    consented --> recording: first audio frame
    recording --> transcribing: stop
    recording --> degraded: ASR crash / client drop
    transcribing --> drafting_diagnosis: POST /generate
    drafting_diagnosis --> diagnosis_review: S/O/A drafted + risk-tiered
    drafting_diagnosis --> transcribing: LLM failure, retry allowed
    diagnosis_review --> drafting_medications: POST /confirm-diagnosis
    drafting_medications --> medication_review: Plan + meds drafted + checked
    drafting_medications --> diagnosis_review: LLM failure
    medication_review --> signed: POST /sign, all gates pass
    signed --> [*]
    degraded --> [*]
```

| Consent state | Effect |
|---|---|
| `pending` | Audio frames are rejected by the gateway |
| `granted` / `granted_verbal_witnessed` | Recording allowed; consent and timestamp are audited |
| `declined` | Recording never starts |

---

## Live Audio Pipeline

The browser captures microphone audio as 16 kHz, 16-bit mono PCM and streams binary frames over a WebSocket. The gateway checks auth and consent before it forwards any audio to the ASR service.

```mermaid
sequenceDiagram
    autonumber
    participant UI as Web UI
    participant GW as Gateway
    participant ASR as ASR service
    participant DB as Postgres

    UI->>GW: WS /api/v1/encounters/{id}/stream with JWT cookie
    GW->>GW: verify identity
    GW->>ASR: WS /transcribe + handshake {encounter_id}
    UI->>GW: {"t":"consent","value":"granted"}
    GW->>DB: consent_recorded + state to consented
    loop every audio frame
        UI->>GW: binary PCM16 frame
        GW->>GW: consent check
        GW->>ASR: forward frame, reconnect if needed
        ASR-->>GW: partial / final TranscriptEvent
        GW-->>UI: relay event to live transcript
    end
    UI->>GW: {"t":"stop"}
    GW->>DB: state to transcribing
    GW->>ASR: stop, force-flush last utterance
    ASR-->>GW: {"t":"done"}
```

Inside the ASR service, each utterance goes through transcription and diarization **in parallel**:

```mermaid
flowchart LR
    A["PCM16 frames"] --> B["Silero VAD<br/>speech / silence"]
    B --> C["VadSegmenter<br/>600 ms silence closes utterance<br/>15 s max"]
    C -->|"ongoing, ~1 s cadence"| D["Partial transcript"]
    C -->|"utterance closed"| E{"asyncio.gather"}
    E --> F["faster-whisper<br/>int8 · beam 1"]
    E --> G["ECAPA-TDNN embedding<br/>online 2-centroid clustering"]
    F --> H["Final TranscriptEvent<br/>text · start_ms · end_ms · speaker · confidence"]
    G --> H
```

- **Models are pre-warmed** at startup (Silero VAD and the SpeechBrain ECAPA classifier are cached singletons), so the WebSocket handshake isn't delayed by model loading.
- **Timestamps** come from VAD-detected utterance boundaries. Segments with `end_ms <= start_ms` are dropped.
- **Speakers** `spk_a` / `spk_b` are relabelled to `clinician` / `patient` before the transcript reaches the LLM.

---

## Two-Phase Note Generation

Note generation is split into two clinician-gated phases. The LLM never drafts a prescription until a clinician has confirmed the diagnosis.

```mermaid
sequenceDiagram
    autonumber
    participant C as Clinician UI
    participant GW as Gateway
    participant LLM as LLM service
    participant SAF as Safety service
    participant R as Redis
    participant DB as Postgres

    rect rgba(70,130,180,0.12)
    note over C,DB: Phase 1 · Diagnosis
    C->>GW: POST /encounters/{id}/generate {segments}
    GW->>LLM: /extract_and_diagnose
    LLM->>LLM: extract_v1.j2 → clinical entities
    LLM->>LLM: diagnose_v1.j2 → Subjective / Objective / Assessment
    LLM->>LLM: validate evidence ids, retry once if invalid
    LLM-->>GW: entities + sections + ungrounded_ids
    GW->>SAF: classify_risk for each Assessment statement
    GW->>R: cache transcript, entities, id_map with TTL
    GW->>DB: NoteVersion v1 · state diagnosis_review
    end

    rect rgba(46,139,87,0.12)
    note over C,DB: Phase 2 · Medications
    C->>GW: POST /confirm-diagnosis {confirmed_diagnosis}
    GW->>LLM: /prescribe with confirmed diagnosis + entities
    LLM-->>GW: Plan statements + medications
    GW->>SAF: resolve each medication
    GW->>SAF: check_interaction for each pair
    GW->>DB: NoteVersion v2 · state medication_review
    end
```

### Prompt design

| Template | Purpose | Key rules |
|---|---|---|
| [`extract_v1.j2`](services/llm/prompts/extract_v1.j2) | Entity extraction | Categories: `symptom_active`, `symptom_denied`, `medication`, `diagnosis`, `plan`, `vital`, `other`. Each entity needs at least one `evidence_span_id`. |
| [`diagnose_v1.j2`](services/llm/prompts/diagnose_v1.j2) | S / O / A drafting | Concise clinical shorthand, no first-person quotes. Patient-reported history goes in **Subjective**; only measurable findings go in **Objective**. Diagnoses should use canonical terminology. |
| [`prescribe_v1.j2`](services/llm/prompts/prescribe_v1.j2) | Plan + medications | Conditioned on the clinician-confirmed diagnosis only |

The LLM runs at `temperature: 0.0` with strict `json_schema` response formatting generated from the shared Pydantic contracts in [`packages/contracts`](packages/contracts/soap_note.schema.json).

---

## Safety Layer

The `safety` service is **fully deterministic**: CSV dictionaries, fuzzy string matching, and one local NLI model. It never calls an LLM (`tests/safety/test_no_llm.py`).

### Diagnosis risk classification

```mermaid
flowchart TD
    A["Proposed condition + extracted symptoms"] --> B{"Red-flag trigger in<br/>condition or any symptom?"}
    B -->|yes| RF["red_flag<br/>red_flag_trigger:name"]
    B -->|no| C["Alias normalisation<br/>diagnosis_aliases.csv"]
    C --> D{"Fuzzy match ≥ 90<br/>against diagnosis_risk_tiers.csv"}
    D -->|no match| RR1["requires_review<br/>no_condition_match"]
    D -->|match| E{"Severity band"}
    E -->|"1–2 · most severe"| RF2["red_flag<br/>severity_band:n"]
    E -->|"3"| RR2["requires_review<br/>severity_band:3"]
    E -->|"4–5 · least severe"| F{"On reviewed<br/>common_allowlist.csv?"}
    F -->|yes| OK["common"]
    F -->|no| RR3["requires_review<br/>not_on_reviewed_allowlist"]
```

The gate **fails closed**: any diagnosis it can't confidently match (for example, a colloquial term like *"severe cold"*) becomes `requires_review`, and the clinician must write their own determination.

### Medication resolution & interactions

```mermaid
flowchart TD
    A["Medication mention"] --> B["Strip dose / form / frequency"]
    B --> C{"Exact generic match?"}
    C -->|no| D{"Brand → composition<br/>Indian brand map"}
    D -->|no| E{"Fuzzy match ≥ 95<br/>generics then brands"}
    E -->|no| U["UNRESOLVED<br/>needs_manual_confirmation"]
    C -->|yes| F["Ingredient list"]
    D -->|yes| F
    E -->|yes| F
    F --> G{"Every ingredient on reviewed<br/>common_medications_allowlist?"}
    G -->|no| U2["needs_manual_confirmation"]
    G -->|yes| H{"High-risk class?<br/>insulin · anticoagulants · etc"}
    H -->|yes| U2
    H -->|no| OK["Auto-approvable"]
    F --> I["Pairwise lookup in<br/>drug_interactions.csv"]
    I --> J["Safety flag with source_ref<br/>must be acknowledged"]
```

### Local knowledge base

| File | Rows | Purpose |
|---|---:|---|
| [`drug_interactions.csv`](services/safety/data/drug_interactions.csv) | 1,150 | Cited pairwise interactions (every row has a `source_ref`) |
| [`high_risk_classes.csv`](services/safety/data/high_risk_classes.csv) | 92 | Drugs that always need manual confirmation |
| [`diagnosis_risk_tiers.csv`](services/safety/data/diagnosis_risk_tiers.csv) | 49 | Canonical condition names with severity bands (from DDXPlus) |
| [`common_medications_allowlist.csv`](services/safety/data/common_medications_allowlist.csv) | 16 | Clinician-reviewed low-risk ingredients |
| [`common_allowlist.csv`](services/safety/data/common_allowlist.csv) | 15 | Clinician-reviewed low-risk conditions |
| [`red_flag_triggers.csv`](services/safety/data/red_flag_triggers.csv) | 11 | Symptoms that always escalate |
| [`diagnosis_aliases.csv`](services/safety/data/diagnosis_aliases.csv) | — | Colloquial → canonical name mapping |

Data provenance is documented in [`services/safety/data/SOURCES.md`](services/safety/data/SOURCES.md).

### Grounding

Two layers of grounding protect against hallucination:

1. **Structural** (LLM service): every cited evidence id must exist in the transcript. If any are invalid, the note is regenerated once. Statements that still fail are listed in `grounding.ungrounded_ids`.
2. **Semantic** (safety service): `cross-encoder/nli-deberta-v3-small` checks that the cited transcript text *entails* the statement. Contradiction **and** neutral both count as ungrounded.

---

## Clinician Review & Sign-off

The review UI shows each statement with its evidence (click to expand the cited transcript spans), its risk tier, and any safety flags. Signing is disabled until every blocking item is resolved. The **server re-validates everything** at `POST /sign`, so the UI is never the only gate.

```mermaid
flowchart TD
    A["POST /encounters/{id}/sign"] --> B{"state == medication_review?"}
    B -->|no| X1["400"]
    B -->|yes| C["For each Assessment statement"]
    C --> D{"Clinician determination provided?"}
    D -->|yes| E["≥ 3 chars · recompute risk tier on final text<br/>audit manual_override with similarity score"]
    D -->|no| F{"Recomputed tier == common?"}
    F -->|no| BLK["Blocking item"]
    F -->|yes| G["OK"]
    E --> G
    G --> H["For each medication"]
    H --> I{"needs_manual_confirmation?"}
    I -->|"yes, no entry"| BLK
    I -->|"entry or auto-approved"| J["Final medication text"]
    J --> K["Re-check interactions on FINAL text"]
    K --> L{"Every interaction acknowledged?"}
    L -->|no| BLK
    L -->|yes| M{"Any blocking items?"}
    BLK --> M
    M -->|yes| X2["400 VALIDATION_FAILED<br/>itemised reasons sent to UI"]
    M -->|no| N["state = signed<br/>clinician_edit NoteVersion<br/>audit state_change"]
    N --> O["Background FHIR push"]
```

- If the safety service is unreachable during sign-off, the gateway returns **503** and does not sign.
- Signed notes are never edited in place. Admins can only append a reasoned **addendum**, which creates a new `admin_correction` version.

---

## EHR Integration (FHIR)

`fhir-gateway` is the **only** component allowed to reach outside the clinical network.

```mermaid
flowchart LR
    A["Signed encounter"] --> B["Fetch encounter + latest note<br/>from gateway"]
    B --> C{"state == signed?"}
    C -->|no| X["400 · refuse"]
    C -->|yes| D["Build transaction Bundle<br/>Encounter · Patient · DocumentReference · MedicationRequest"]
    D --> E["Deterministic uuid5 ids<br/>+ Idempotency-Key"]
    E --> F["Validate with fhir.resources"]
    F --> G{"Target matches<br/>FHIR_ALLOWLIST_HOST:PORT?"}
    G -->|no| X2["403 · egress restricted"]
    G -->|yes| H["POST with optional mTLS<br/>3 retries"]
    H -->|ok| S["ehr_status = synced"]
    H -->|fail| Q["ehr_status = queued_local<br/>POST /retry_sync"]
```

`DocumentReference` resources carry provenance meta tags (`statement-type`, `risk-tier`). Medications that needed manual entry are annotated in the `MedicationRequest`.

---

## Data Model & Auditability

```mermaid
erDiagram
    ROLES ||--o{ USERS : has
    ENCOUNTERS ||--o{ NOTE_VERSIONS : "versioned as"
    ENCOUNTERS ||--o{ AUDIT_LOG : "audited by"
    ENCOUNTERS ||--o{ MEDICATIONS : prescribes
    NOTE_VERSIONS ||--o{ MEDICATIONS : contains

    USERS {
        uuid id PK
        string username
        string password_hash "bcrypt"
        string role_id FK "clinician | admin | auditor"
    }
    ENCOUNTERS {
        uuid id PK
        string clinician_id
        string patient_ref
        string consent_state
        string state
        string ehr_status "pending | synced | queued_local"
        string degraded_reason
        bool retention_opt_in
    }
    NOTE_VERSIONS {
        uuid id PK
        uuid encounter_id FK
        int version
        string source "ai | clinician_edit | admin_correction"
        jsonb content_jsonb
        string model_name
        string model_hash
        string prompt_version
    }
    AUDIT_LOG {
        bigint id PK
        uuid encounter_id FK
        string actor
        string action
        string before_hash "sha256"
        string after_hash "sha256"
        jsonb diff_jsonb
        timestamptz created_at
    }
    DRUG_INTERACTIONS {
        uuid id PK
        string ingredient_a
        string ingredient_b
        string severity
        string source_ref "NOT NULL"
    }
```

**Audit guarantees**

- `audit_log` is **append-only at the database level**: the `scribe_app` role has `INSERT, SELECT` only, and `UPDATE, DELETE` are revoked. Migrations run as the Postgres superuser so these revokes actually apply to the app role (`tests/security/test_audit_immutable.py`).
- Every row stores SHA-256 hashes of the before/after state plus a JSON diff.
- `manual_override` rows record the AI text, the clinician text, the recomputed risk tier, and an `ai_similarity_score` / `matches_ai_draft` flag. This makes rubber-stamping visible.
- Every note version records `model_name`, `model_hash`, and `prompt_version`, so you can always answer *"what did the AI originally draft, and with which model?"*

**Retention tiers** (ADR-0002)

| Tier | Data | Retention |
|---|---|---|
| 1 | Audio | **Never** written to disk, in any configuration |
| 2 | Transcript | Redis with TTL (`TRANSCRIPT_TTL_SECONDS`); persistent only on per-encounter opt-in |
| 3 | Note versions + audit log | Permanent: diffs of clinical text, never audio |

---

## Privacy & Security Controls

| Control | Implementation |
|---|---|
| Network isolation | `clinic` network is `internal: true`; only `gateway` and `fhir-gateway` also join `edge` |
| Offline models | `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` everywhere; model weights fetched at build time only (ADR-0015) |
| Authentication | bcrypt password hashes, HS256 JWT in an `httponly` cookie, 12 h expiry; startup refuses `JWT_SECRET` under 32 bytes |
| CSRF | Double-submit cookie: `csrf_token` cookie must match the `x-csrf-token` header on every mutating request |
| Row-Level Security | Each DB session sets `app.current_user_id` / `app.current_role_id` from the **verified JWT** and then `SET ROLE scribe_app`. Roles cannot be self-asserted. |
| Role separation | `clinician` drafts and signs · `admin` appends addenda · `auditor` reads audit trails |
| Least privilege DB | App role cannot mutate audit rows; migrations run as superuser |
| Hardened prod overlay | `docker-compose.prod.yml`: read-only ASR filesystem, `noexec` tmpfs, memory limits, log rotation |
| Egress verification | `make verify-offline` runs the egress test suite with `--network none` |

---

## Testing & Evaluation

```mermaid
flowchart LR
    T["tests/"] --> SEC["security<br/>no-egress · no-cloud-deps · audit immutability<br/>log redaction · CSRF · RLS identity"]
    T --> GWT["gateway<br/>state machine · auth · JWT · risk gate E2E<br/>sign 503 · interactions · edits"]
    T --> SAFT["safety<br/>diagnosis tiers · drug resolution<br/>adversarial pairs · grounding · no-LLM"]
    T --> LLMT["llm<br/>10 regression fixtures · clinical shorthand"]
    T --> ASRT["asr<br/>WS events · no disk persistence · latency"]
    T --> CH["chaos<br/>ASR crash · EHR unreachable · GPU OOM fallback"]
    T --> FAIR["fairness<br/>code-switch gap · ADR-0006"]
    T --> E2E["e2e + Playwright<br/>review safety · consent gate · signing"]
```

| Command | What it does |
|---|---|
| `make test` | Full pytest suite inside the gateway container + web tests |
| `make verify-offline` | Proves zero outbound egress except the FHIR allowlist |
| `make eval DATASET=...` | Runs the evaluation harness |
| `make contracts` | Regenerates Python + TS types from `soap_note.schema.json` |
| `npm run test:e2e` (in `apps/web`) | Playwright UI safety tests |

**Evaluation harness** ([`eval/harness/run.py`](eval/harness/run.py)) reports measured metrics, not quoted industry averages (ADR-0007, ADR-0008):

| Metric | Description |
|---|---|
| WER / CER | ASR accuracy against reference transcripts (`jiwer`) |
| Medication P / R / F1 / exact match | Prescription extraction accuracy |
| Unsupported-claim rate | Per SOAP section: the hallucination measure |
| Omission rate | Clinically relevant content missed |
| Risk-escalation agreement | Safety tier vs reference |
| Latency | Per pipeline stage |
| Energy per consultation | GPU power sampled via `nvidia-smi` |
| Diarization accuracy | [`run_diarization_eval.py`](eval/harness/run_diarization_eval.py) |

---

## Architecture Decision Records

| ADR | Decision |
|---|---|
| [0001](docs/decisions/0001-egress-policy.md) | Egress policy: "egress-denied, LAN-isolated", not "air-gapped" |
| [0002](docs/decisions/0002-retention-tiers.md) | Three-tier data retention |
| [0003](docs/decisions/0003-diagnostic-copilot-scope.md) | "Diagnostic copilot" re-scoped to non-autonomous decision support |
| [0004](docs/decisions/0004-drug-data-sources.md) | Drug interaction and ingredient data sources (local only) |
| [0005](docs/decisions/0005-model-choice-llama3-8b.md) | Fixed model: Llama 3 8B Instruct |
| [0006](docs/decisions/0006-hinglish-evaluation.md) | Mandatory Hindi–English code-switching evaluation subset |
| [0007](docs/decisions/0007-hallucination-definition.md) | Hallucination is measured, not quoted |
| [0008](docs/decisions/0008-energy-measurement-method.md) | Energy-per-consultation is measured |
| [0009](docs/decisions/0009-form-numbering-fix.md) | Form numbering fix |
| [0013](docs/decisions/0013-speaker-diarization.md) | Speaker diarization strategy |
| [0015](docs/decisions/0015-speaker-embedding-build-time-downloads.md) | Build-time model downloads are not runtime egress |

> ADRs and `eval/datasets/` are **human-owned**. Changes to `packages/contracts/` need an explicit, ADR-backed instruction.

---

## Repository Structure

```text
clinical-scribe/
├── apps/
│   └── web/                     # React 19 + Vite + Tailwind clinician UI
│       ├── src/pages/           # Start · Consultation · Review · AuditDashboard · EncounterAuditDetail
│       ├── src/components/      # consultation/ (consent, recorder, live transcript) · review/ (SOAP, evidence, sign)
│       ├── src/hooks/           # useAudioCapture · useWebSocket · useTranscript · useReviewState
│       ├── e2e/ · tests/        # Playwright safety + review specs
│       └── nginx.conf           # Serves SPA, proxies /api (REST + WS) to gateway
├── services/
│   ├── gateway/                 # Orchestrator: auth, RLS, state machine, audit, WS relay
│   │   └── alembic/versions/    # Schema, RLS policies, seed users, ehr_status
│   ├── asr/                     # VAD + faster-whisper + ECAPA diarization
│   ├── llm/                     # Prompt templates (prompts/*.j2) + structured generation
│   ├── safety/                  # Deterministic risk/drug/interaction/grounding checks
│   │   └── data/                # Local, cited CSV knowledge base
│   └── fhir-gateway/            # Sole egress point → FHIR Bundle push
├── packages/
│   └── contracts/               # soap_note.schema.json → generated Pydantic + TS types
├── tests/                       # security · gateway · safety · llm · asr · chaos · fairness · e2e
├── eval/
│   ├── harness/                 # Metrics harness (WER, hallucination, energy, diarization)
│   └── datasets/                # Human-owned evaluation data (do not edit)
├── scripts/                     # Model download, data seeding, dev DB reset, eval helpers
├── infra/                       # DB init, firewall, observability, secrets placeholders
├── docs/
│   ├── architecture.md
│   └── decisions/               # ADRs (human-owned)
├── docker-compose.yml           # Dev stack
├── docker-compose.prod.yml      # Hardened production overlay
├── Makefile
└── AGENTS.md                    # Standing rules for coding agents
```

---

## Getting Started

### Prerequisites

- Docker + Docker Compose
- NVIDIA GPU + NVIDIA Container Toolkit (for the `ollama` service)
- Python 3.12 with `huggingface_hub` (one-time model download only)
- ~20 GB free disk for images and model weights

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```ini
JWT_SECRET=<at least 32 random bytes>   # python -c "import secrets; print(secrets.token_urlsafe(48))"
POSTGRES_SUPERUSER_PASSWORD=<secret>
POSTGRES_PASSWORD=<secret>
LLM_BACKEND=http://ollama:11434/v1/chat/completions
LLM_MODEL_NAME=llama3.1:latest
```

> [!IMPORTANT]
> `LLM_BACKEND` must be the full OpenAI-compatible chat-completions URL. The LLM service rejects values that don't start with `http`.

### 2. Fetch build-time models (one-time, needs internet)

Per ADR-0015, these are downloaded on the host **before** the build and baked into images. They are never fetched at runtime.

```bash
pip install huggingface_hub
python scripts/download_ecapa.py      # → services/asr/models/spkrec-ecapa-voxceleb
python scripts/download_deberta.py    # → services/safety/models/nli-deberta-v3-small
```

### 3. Provision the LLM weights (one-time)

`ollama` sits on the egress-denied `clinic` network, so it **cannot** pull models itself. Seed its volume from a temporary container instead:

```bash
docker volume create clinical-scribe_ollama_data
docker run -d --name ollama-seed -v clinical-scribe_ollama_data:/root/.ollama ollama/ollama
docker exec ollama-seed ollama pull llama3.1
docker rm -f ollama-seed
```

### 4. Build and start the stack

```bash
docker compose up --build -d
```

### 5. Run migrations (creates schema, audit permissions, RLS, seed users)

```bash
docker compose exec -e POSTGRES_SUPERUSER=postgres \
  -e POSTGRES_SUPERUSER_PASSWORD=<your superuser password> \
  gateway alembic -c /app/alembic.ini upgrade head
```

On Windows you can instead run the dev-only reset script, which wipes **only** the Postgres volume and re-migrates:

```powershell
./scripts/reset_dev_db.ps1
```

### 6. Open the app

| URL | What |
|---|---|
| http://localhost:5173 | Clinician UI |
| http://localhost:8000/docs | Gateway OpenAPI docs |

Seeded dev accounts (passwords come from `.env`):

| Username | Role | Password variable |
|---|---|---|
| `dr-martinez` | clinician | `SEED_CLINICIAN_PASSWORD` |
| `dr-jones` | clinician (RLS test user) | `SEED_CLINICIAN_PASSWORD` |
| `admin` | admin | `SEED_ADMIN_PASSWORD` |
| `auditor` | auditor | `SEED_ADMIN_PASSWORD` |

> [!WARNING]
> Default seed passwords are for local development only. The migration prints a warning when they're used.

### Key configuration

| Variable | Default | Purpose |
|---|---|---|
| `WHISPER_MODEL` | `small` | `tiny` / `small` are baked into the ASR image |
| `UTTERANCE_SILENCE_MS` | `600` | Silence that closes an utterance |
| `TRANSCRIPT_TTL_SECONDS` | `3600` | Redis transcript lifetime |
| `FUZZY_MATCH_MIN_CONFIDENCE` | `0.72` | Drug-name fuzzy threshold |
| `FHIR_ALLOWLIST_HOST` / `_PORT` | — | The single permitted egress target |
| `FHIR_MTLS_CERT_PATH` / `_KEY_PATH` | — | Client certs for the EHR push |
| `LLM_FALLBACK_BACKEND` / `_MODEL` | — | Smaller-tier fallback on LLM failure |
| `AUDIO_RETENTION` | `never` | Must always be `never` |
| `REDACT_CLINICAL_TEXT_IN_LOGS` | `true` | Must always be `true` |

---

## API Reference

All gateway routes are under `/api/v1`. Mutating requests need the JWT cookie **and** a matching `x-csrf-token` header.

| Method | Route | Description |
|---|---|---|
| `POST` | `/auth/login` | Issue JWT + CSRF cookies |
| `POST` | `/encounters` | Create encounter (`created`, consent `pending`) |
| `GET` | `/encounters` | List encounters (RLS-scoped) |
| `GET` | `/encounters/{id}` | Encounter, latest note, transcript |
| `WS` | `/encounters/{id}/stream` | Consent, audio frames, stop · live transcript events |
| `POST` | `/encounters/{id}/generate` | Phase 1: draft S / O / A |
| `POST` | `/encounters/{id}/confirm-diagnosis` | Phase 2: draft Plan + medications |
| `GET` / `PATCH` | `/encounters/{id}/note` | Read / edit latest note |
| `POST` | `/encounters/{id}/statements` | Add a clinician-entered statement |
| `POST` | `/encounters/{id}/acknowledge-flag` | Acknowledge a safety flag (audited) |
| `POST` | `/encounters/{id}/sign` | Validate all gates and sign |
| `POST` | `/encounters/{id}/retry_sync` | Retry a queued FHIR push |
| `POST` | `/encounters/{id}/addendum` | Admin-only reasoned correction |
| `GET` | `/encounters/{id}/audit` | Full audit trail |

**Internal service endpoints** (reachable only on the `clinic` network)

| Service | Route |
|---|---|
| asr | `WS /transcribe` |
| llm | `POST /extract_and_diagnose`, `POST /prescribe` |
| safety | `POST /api/v1/safety/classify_risk`, `/resolve`, `/check_interaction`, `/verify_grounding` |
| fhir-gateway | `POST /push` |

---

## Contributing

Read [`AGENTS.md`](AGENTS.md) before contributing. A change is **done** only when:

1. `mypy` / `tsc` pass and `ruff` / `eslint` are clean.
2. Unit tests are written and passing, plus an integration test if the change crosses a service boundary.
3. `make verify-offline` still passes.
4. UI changes are browser-verified, with a screenshot.
5. The change comes with a one-paragraph summary of what changed and why.

Never add hosted AI, speech, or telemetry dependencies. Never write audio to disk. Never log clinical text. Never add an "approve all" action. If a requirement is ambiguous, **stop and ask**: this is a safety-relevant medical system.

---

<p align="center"><sub>Built local-first. The AI drafts, deterministic code gates, the clinician decides.</sub></p>
