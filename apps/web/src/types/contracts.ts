/**
 * Frontend type definitions — aligned with packages/contracts/ts/soap_note.ts
 * and services/gateway/src/models.py
 *
 * We re-declare types here rather than importing from packages/contracts
 * because the contract package is not set up as a local npm workspace dep.
 * All types are kept in strict sync with the canonical JSON Schema.
 */

/* ─── Encounter State Machine ──────────────────────────── */

export type EncounterState =
  | 'created'
  | 'consented'
  | 'recording'
  | 'transcribing'
  | 'drafting'
  | 'ready'
  | 'signed'
  | 'degraded'
  | 'cancelled';

export type ConsentState =
  | 'pending'
  | 'granted'
  | 'granted_verbal_witnessed'
  | 'declined';

export interface Encounter {
  id: string;
  state: EncounterState;
  consent_state: ConsentState;
}

/* ─── Transcript Events (from ASR via gateway WS) ──────── */

export interface TranscriptEvent {
  id?: string;
  type: 'partial' | 'final';
  text: string;
  start_ms: number;
  end_ms: number;
  confidence: number;
  speaker?: string | null;
}

/* ─── WebSocket Messages (client → gateway) ─────────────── */

export type WsOutboundMessage =
  | { t: 'consent'; value: ConsentState }
  | { t: 'audio'; data: string }
  | { t: 'stop' }
  | { t: 'swap' }
  | { t: 'error'; reason: string };

/* ─── SOAP Note — mirrors soap_note.schema.json exactly ── */

export interface SoapStatement {
  id: string;
  text: string;
  /** Non-empty by design — minItems: 1 */
  evidence: [string, ...string[]];
  confidence?: number;
}

export type StatementList = SoapStatement[];

export interface SafetyFlag {
  severity: 'low' | 'moderate' | 'high';
  type: 'interaction' | 'dose_range' | 'unresolved_medication';
  pair?: string[];
  /** Mandatory citation. Never null. */
  source_ref: string;
  message: string;
}

export interface Medication {
  id: string;
  verbatim: string;
  ingredient_id?: string | null;
  match_confidence?: number;
  needs_manual_confirmation?: boolean;
  dose?: { value?: number; unit?: string };
  frequency?: string;
  route?: string;
  duration_days?: number;
  /** minItems: 1 */
  evidence: [string, ...string[]];
  flags: SafetyFlag[];
}

export interface SoapNote {
  encounter_id: string;
  model: {
    name: 'llama-3-8b-instruct';
    quant: string;
    prompt_version: string;
  };
  generated_at: string;
  sections: {
    subjective: StatementList;
    objective: StatementList;
    assessment: StatementList;
    plan: StatementList;
  };
  medications?: Medication[];
  differential_considerations?: {
    label: string;
    trigger_spans: [string, ...string[]];
    rationale: string;
  }[];
  safety_flags?: SafetyFlag[];
  grounding: {
    statements_total: number;
    ungrounded: number;
    ungrounded_ids: string[];
  };
}

/* ─── Review State (frontend-only tracking) ──────────────── */

export interface ReviewState {
  /** Map of statement id → whether the clinician has reviewed/confirmed it */
  statementReviews: Record<string, boolean>;
  /** Map of "medication_id:flag_index" → whether the flag was individually acknowledged */
  flagAcknowledgments: Record<string, boolean>;
  /** Map of section key → whether the section is approved */
  sectionApprovals: Record<string, boolean>;
  /** Map of section key → the custom edited text for that section (if any) */
  sectionEdits: Record<string, string>;
  /** Computed: true only when all ungrounded are double-confirmed AND all flags acknowledged */
  canSign: boolean;
}

/* ─── API Response Types ─────────────────────────────────── */

export interface CreateEncounterResponse {
  id: string;
  state: string;
  consent_state: string;
}

export interface AuditEntry {
  action: string;
  actor: string;
  diff: Record<string, unknown> | null;
  created_at: string;
}
