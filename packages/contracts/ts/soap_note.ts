/* eslint-disable */
/**
 * Generated from soap_note.schema.json
 * Re-generated after Phase 3 schema change: sections are now objects
 * with { statements, insufficient_content, reason } instead of bare arrays.
 *
 * DO NOT MODIFY IT BY HAND. Instead, modify the source JSONSchema file,
 * and run the generator to regenerate this file.
 */

export interface StatementListItem {
  id: string;
  text: string;
  /**
   * Non-empty by design — a statement with no cited transcript span cannot exist.
   * This is the schema-level enforcement of 'no hallucinated claims.'
   *
   * @minItems 1
   */
  evidence: [string, ...string[]];
  confidence?: number;
}

export interface SoapSection {
  statements: StatementListItem[];
  /**
   * True when the transcript contains nothing relevant to this section.
   * When true, statements must be empty and reason must be non-null.
   */
  insufficient_content: boolean;
  /**
   * One-line explanation of why this section has no content, e.g.
   * 'Not discussed in this consultation'. Required when
   * insufficient_content is true, null otherwise.
   */
  reason?: string | null;
}

export interface SoapNote {
  encounter_id: string;
  model: {
    name: "llama-3-8b-instruct";
    quant: string;
    prompt_version: string;
  };
  generated_at: string;
  sections: {
    subjective: SoapSection;
    objective: SoapSection;
    assessment: SoapSection;
    plan: SoapSection;
  };
  medications?: {
    id: string;
    verbatim: string;
    /**
     * FK into the local ingredient_dictionary table. Null if unresolved.
     */
    ingredient_id?: string | null;
    match_confidence?: number;
    needs_manual_confirmation?: boolean;
    dose?: {
      value?: number;
      unit?: string;
    };
    frequency?: string;
    route?: string;
    duration_days?: number;
    /**
     * @minItems 1
     */
    evidence: [string, ...string[]];
    flags: SafetyFlag[];
  }[];
  differential_considerations?: {
    label: string;
    /**
     * @minItems 1
     */
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

export interface SafetyFlag {
  severity: "low" | "moderate" | "high";
  type: "interaction" | "dose_range" | "unresolved_medication";
  pair?: string[];
  /**
   * Mandatory citation, e.g. 'ONC-HighPriority#412' or 'DDInter2#88014'.
   * Never null — an interaction flag with no source is not permitted.
   */
  source_ref: string;
  message: string;
}
