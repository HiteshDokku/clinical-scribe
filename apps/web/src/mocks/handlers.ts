import type { CreateEncounterResponse, SoapNote, TranscriptEvent } from '@/types/contracts';
import { MOCK_SOAP_NOTE } from './soapNote';
import { MOCK_TRANSCRIPT_SEQUENCE } from './transcript';

/**
 * Whether mock mode is active. Set VITE_MOCK_API=true in .env or env vars.
 * Always true in test/demo environments where the gateway is not running.
 */
export const IS_MOCK = import.meta.env.VITE_MOCK_API === 'true' || import.meta.env.MODE === 'test';

/** Simulates POST /api/v1/encounters */
export function mockCreateEncounter(): CreateEncounterResponse {
  return {
    id: `mock-${Date.now().toString(36)}`,
    state: 'created',
    consent_state: 'pending',
  };
}

/** Returns the mock SOAP note fixture */
export function mockGetSoapNote(): SoapNote {
  return MOCK_SOAP_NOTE;
}

/**
 * Simulates WebSocket transcript streaming.
 * Calls onEvent for each transcript event with realistic delays.
 * Returns a cleanup function.
 */
export function mockTranscriptStream(
  onEvent: (event: TranscriptEvent) => void,
  onDone: () => void,
): () => void {
  const timers: ReturnType<typeof setTimeout>[] = [];
  let cumulativeDelay = 0;

  for (const item of MOCK_TRANSCRIPT_SEQUENCE) {
    cumulativeDelay += item.delay;
    const timer = setTimeout(() => {
      onEvent(item.event);
    }, cumulativeDelay);
    timers.push(timer);
  }

  // Signal done after all events
  const doneTimer = setTimeout(onDone, cumulativeDelay + 1000);
  timers.push(doneTimer);

  return () => {
    for (const t of timers) clearTimeout(t);
  };
}
