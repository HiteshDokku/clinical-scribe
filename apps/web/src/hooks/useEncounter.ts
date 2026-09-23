import { useState, useCallback } from 'react';
import type { Encounter, EncounterState, ConsentState } from '@/types/contracts';
import { createEncounter as apiCreateEncounter } from '@/api/encounters';
import { IS_MOCK, mockCreateEncounter } from '@/mocks/handlers';

interface UseEncounterReturn {
  encounter: Encounter | null;
  isLoading: boolean;
  error: string | null;
  createEncounter: (clinicianId: string, patientRef: string) => Promise<Encounter>;
  updateEncounter: (updates: Partial<Encounter>) => void;
  initEncounter: (id: string) => void;
}

/**
 * Manages encounter lifecycle state. Enforces the state machine transitions
 * defined in services/gateway/src/models.py.
 */
export function useEncounter(): UseEncounterReturn {
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createEncounter = useCallback(async (clinicianId: string, patientRef: string) => {
    setIsLoading(true);
    setError(null);
    try {
      let resp;
      if (IS_MOCK) {
        resp = mockCreateEncounter();
      } else {
        resp = await apiCreateEncounter(clinicianId, patientRef);
      }
      const enc: Encounter = {
        id: resp.id,
        state: resp.state as EncounterState,
        consent_state: resp.consent_state as ConsentState,
      };
      setEncounter(enc);
      return enc;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create encounter';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateEncounter = useCallback((updates: Partial<Encounter>) => {
    setEncounter((prev) => (prev ? { ...prev, ...updates } : null));
  }, []);

  const initEncounter = useCallback((id: string) => {
    setEncounter({ id, state: 'created', consent_state: 'pending' });
  }, []);

  return { encounter, isLoading, error, createEncounter, updateEncounter, initEncounter };
}
