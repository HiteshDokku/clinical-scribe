import type { CreateEncounterResponse } from '@/types/contracts';

const BASE = '/api/v1';

export async function createEncounter(
  clinicianId: string,
  patientRef: string,
): Promise<CreateEncounterResponse> {
  const res = await fetch(`${BASE}/encounters`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ clinician_id: clinicianId, patient_ref: patientRef }),
  });
  if (!res.ok) throw new Error(`Failed to create encounter: ${res.status}`);
  return res.json() as Promise<CreateEncounterResponse>;
}

import type { TranscriptEvent, SoapNote } from '@/types/contracts';

export async function generateNote(encounterId: string, segments: TranscriptEvent[]): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/encounters/${encounterId}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ segments }),
  });
  if (!res.ok) throw new Error(`Failed to generate note: ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}

export async function getEncounter(encounterId: string): Promise<{
  id: string;
  state: string;
  note: SoapNote;
  transcript: TranscriptEvent[];
}> {
  const res = await fetch(`${BASE}/encounters/${encounterId}`);
  if (!res.ok) throw new Error(`Failed to get encounter: ${res.status}`);
  return res.json();
}

export async function confirmDiagnosis(encounterId: string, confirmedDiagnosis: string): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/encounters/${encounterId}/confirm-diagnosis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmed_diagnosis: confirmedDiagnosis }),
  });
  if (!res.ok) throw new Error(`Failed to confirm diagnosis: ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}

export async function signNote(encounterId: string, editedSections?: Record<string, string>): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/encounters/${encounterId}/sign`, {
    method: 'POST',
    headers: editedSections ? { 'Content-Type': 'application/json' } : undefined,
    body: editedSections ? JSON.stringify({ edits: editedSections }) : undefined,
  });
  if (!res.ok) throw new Error(`Failed to sign note: ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}

export async function getAudit(
  encounterId: string,
): Promise<{ action: string; actor: string; diff: unknown; created_at: string }[]> {
  const res = await fetch(`${BASE}/encounters/${encounterId}/audit`);
  if (!res.ok) throw new Error(`Failed to get audit: ${res.status}`);
  return res.json() as Promise<{ action: string; actor: string; diff: unknown; created_at: string }[]>;
}
