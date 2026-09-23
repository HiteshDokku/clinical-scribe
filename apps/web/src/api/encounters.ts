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

export async function getNote(encounterId: string): Promise<SoapNote> {
  const res = await fetch(`${BASE}/encounters/${encounterId}/note`);
  if (!res.ok) throw new Error(`Failed to get note: ${res.status}`);
  return res.json() as Promise<SoapNote>;
}

export async function signNote(encounterId: string): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/encounters/${encounterId}/sign`, {
    method: 'POST',
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
