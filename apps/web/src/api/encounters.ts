import type { CreateEncounterResponse } from '@/types/contracts';

const BASE = '/api/v1';

async function apiFetch(url: string, options: RequestInit = {}) {
  const demoRole = localStorage.getItem('demo_role') || 'clinician';
  const headers = new Headers(options.headers || {});
  headers.set('X-Mock-Role', demoRole);
  
  return fetch(url, { ...options, headers });
}

export async function createEncounter(
  clinicianId: string,
  patientRef: string,
): Promise<CreateEncounterResponse> {
  const res = await apiFetch(`${BASE}/encounters`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'X-User-Id': clinicianId,
      'X-Role-Id': 'clinician'
    },
    body: JSON.stringify({ clinician_id: clinicianId, patient_ref: patientRef }),
  });
  if (!res.ok) throw new Error(`Failed to create encounter: ${res.status}`);
  return res.json() as Promise<CreateEncounterResponse>;
}

import type { TranscriptEvent, SoapNote } from '@/types/contracts';

export async function generateNote(encounterId: string, segments: TranscriptEvent[]): Promise<{ status: string }> {
  const res = await apiFetch(`${BASE}/encounters/${encounterId}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ segments }),
  });
  if (!res.ok) throw new Error(`Failed to generate note: ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}

export async function getEncounter(
  encounterId: string,
  clinicianId?: string,
  roleId?: string,
): Promise<{
  id: string;
  state: string;
  note: SoapNote;
  transcript: TranscriptEvent[];
}> {
  const headers: Record<string, string> = {};
  if (clinicianId) headers['X-User-Id'] = clinicianId;
  if (roleId) headers['X-Role-Id'] = roleId;

  const res = await apiFetch(`${BASE}/encounters/${encounterId}`, { headers });
  if (!res.ok) throw new Error(`Failed to get encounter: ${res.status}`);
  return res.json();
}

export async function confirmDiagnosis(encounterId: string, confirmedDiagnosis: string): Promise<{ status: string }> {
  const res = await apiFetch(`${BASE}/encounters/${encounterId}/confirm-diagnosis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmed_diagnosis: confirmedDiagnosis }),
  });
  if (!res.ok) throw new Error(`Failed to confirm diagnosis: ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}

export async function signNote(encounterId: string, editedSections?: Record<string, string>): Promise<{ status: string }> {
  const res = await apiFetch(`${BASE}/encounters/${encounterId}/sign`, {
    method: 'POST',
    headers: editedSections ? { 'Content-Type': 'application/json' } : undefined,
    body: editedSections ? JSON.stringify({ edits: editedSections }) : undefined,
  });
  if (!res.ok) throw new Error(`Failed to sign note: ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}

export async function getAudit(
  encounterId: string,
  clinicianId?: string,
  roleId?: string,
): Promise<{ action: string; actor: string; diff: unknown; created_at: string }[]> {
  const headers: Record<string, string> = {};
  if (clinicianId) headers['X-User-Id'] = clinicianId;
  if (roleId) headers['X-Role-Id'] = roleId;

  const res = await apiFetch(`${BASE}/encounters/${encounterId}/audit`, { headers });
  if (!res.ok) throw new Error(`Failed to get audit: ${res.status}`);
  return res.json() as Promise<{ action: string; actor: string; diff: unknown; created_at: string }[]>;
}

export async function getEncounters(
  clinicianId?: string,
  roleId?: string,
  state?: string,
): Promise<{ id: string; patient_ref: string; created_at: string; state: string; confirmed_diagnosis_summary: string }[]> {
  const headers: Record<string, string> = {};
  if (clinicianId) headers['X-User-Id'] = clinicianId;
  if (roleId) headers['X-Role-Id'] = roleId;
  
  const url = state ? `${BASE}/encounters?state=${state}&limit=100` : `${BASE}/encounters?limit=100`;
  const res = await apiFetch(url, { headers });
  if (!res.ok) throw new Error(`Failed to list encounters: ${res.status}`);
  return res.json();
}

export async function appendAddendum(encounterId: string, section: string, correctedText: string, reason: string): Promise<{ status: string }> {
  const res = await apiFetch(`${BASE}/encounters/${encounterId}/addendum`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ section, corrected_text: correctedText, reason }),
  });
  if (!res.ok) throw new Error(`Failed to append addendum: ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}
