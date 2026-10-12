import type { CreateEncounterResponse } from '@/types/contracts';

const BASE = '/api/v1';

let cachedToken: string | null = null;

async function getAuthToken(): Promise<string> {
  if (cachedToken) return cachedToken;
  const demoRole = localStorage.getItem('demo_role') || 'clinician';
  const username = demoRole === 'admin' ? 'admin' : 'dr-martinez';
  const password = demoRole === 'admin' ? 'dev_admin_pass' : 'dev_clinician_pass';
  
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (!res.ok) throw new Error("Failed to login");
  const data = await res.json();
  cachedToken = data.access_token;
  if (!cachedToken) throw new Error("No token returned");
  return cachedToken;
}

async function apiFetch(url: string, options: RequestInit = {}) {
  const token = await getAuthToken();
  const headers = new Headers(options.headers || {});
  headers.set('Authorization', `Bearer ${token}`);
  
  // Extract csrf_token from cookies
  const match = document.cookie.match(new RegExp('(^| )csrf_token=([^;]+)'));
  if (match && match[2]) {
    headers.set('X-CSRF-Token', match[2] as string);
  }
  
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

export class ApiError extends Error {
  status: number;
  data: any;
  items: Array<{ kind: string; id: string; reason: string }>;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.items = (data && Array.isArray(data.items)) ? data.items : [];
  }
}

export async function confirmDiagnosis(encounterId: string, confirmedDiagnosis: string): Promise<{ status: string }> {
  const res = await apiFetch(`${BASE}/encounters/${encounterId}/confirm-diagnosis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmed_diagnosis: confirmedDiagnosis }),
  });
  if (!res.ok) {
    let errBody: any = null;
    try {
      errBody = await res.json();
    } catch (e) {}
    const detail = errBody?.detail;
    const msg = typeof detail === 'string' ? detail : detail?.message || `Failed to confirm diagnosis: ${res.status}`;
    throw new ApiError(msg, res.status, detail);
  }
  return res.json() as Promise<{ status: string }>;
}

export async function signNote(
  encounterId: string,
  editedSections?: Record<string, string>,
  statementDeterminations?: Record<string, string>,
  medicationEntries?: Record<string, string>,
  acknowledgedFlags?: string[]
): Promise<{ status: string }> {
  const body: any = {};
  if (editedSections) body.edits = editedSections;
  if (statementDeterminations) body.statement_determinations = statementDeterminations;
  if (medicationEntries) body.medication_entries = medicationEntries;
  if (acknowledgedFlags && acknowledgedFlags.length > 0) body.acknowledged_flags = acknowledgedFlags;
  
  const res = await apiFetch(`${BASE}/encounters/${encounterId}/sign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let errBody: any = null;
    try {
      errBody = await res.json();
    } catch (e) {}
    const detail = errBody?.detail;
    const msg = typeof detail === 'string' ? detail : detail?.message || `Failed to sign note: ${res.status}`;
    throw new ApiError(msg, res.status, detail);
  }
  return res.json() as Promise<{ status: string }>;
}

export async function acknowledgeFlag(encounterId: string, flagId: string): Promise<{ status: string }> {
  const res = await apiFetch(`${BASE}/encounters/${encounterId}/acknowledge-flag`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ flag_id: flagId }),
  });
  if (!res.ok) throw new Error(`Failed to acknowledge flag: ${res.status}`);
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

export async function addStatement(
  encounterId: string,
  section: string,
  text: string
): Promise<SoapNote> {
  const res = await apiFetch(`${BASE}/encounters/${encounterId}/statements`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ section, text }),
  });
  if (!res.ok) {
    let errBody: any = null;
    try {
      errBody = await res.json();
    } catch (e) {}
    let msg = `Failed to add statement: ${res.status}`;
    if (typeof errBody?.detail === 'string') {
      msg = errBody.detail;
    } else if (Array.isArray(errBody?.detail) && errBody.detail.length > 0) {
      msg = errBody.detail[0]?.msg || msg;
    } else if (errBody?.detail?.message) {
      msg = errBody.detail.message;
    }
    throw new ApiError(msg, res.status, errBody?.detail);
  }
  return res.json() as Promise<SoapNote>;
}

