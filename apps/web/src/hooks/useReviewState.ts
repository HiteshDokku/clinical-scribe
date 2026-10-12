import { useState, useCallback, useMemo } from 'react';
import type { SoapNote, ReviewState } from '@/types/contracts';

export interface BlockingItem {
  itemId: string;
  reason: string;
}

export interface ReviewStateData {
  statementReviews: Record<string, boolean>;
  flagAcknowledgments: Record<string, boolean>;
  statementDeterminations: Record<string, string>;
  medicationEntries: Record<string, string>;
}

export type ReviewPhase = 'diagnosis' | 'medication' | 'all';

/**
 * Pure function that evaluates whether a note can be advanced or signed,
 * returning structured blocking items with element IDs for scrolling/highlighting.
 */
export function computeReviewState(
  soapNote: SoapNote | null,
  phase: ReviewPhase,
  state: ReviewStateData,
): { canSign: boolean; blockingReasons: string[]; blockingItems: BlockingItem[] } {
  if (!soapNote) {
    return {
      canSign: false,
      blockingReasons: ['No note loaded'],
      blockingItems: [{ itemId: 'none', reason: 'No note loaded' }],
    };
  }

  const blockingItems: BlockingItem[] = [];

  // Diagnosis phase sections: subjective, objective, assessment
  if (phase === 'diagnosis' || phase === 'all') {
    const diagSections: Array<'subjective' | 'objective' | 'assessment'> = ['subjective', 'objective', 'assessment'];
    for (const secKey of diagSections) {
      const section = soapNote.sections[secKey];
      if (!section) continue;
      // Insufficient content sections count as complete
      if (section.insufficient_content) continue;

      for (let i = 0; i < section.statements.length; i++) {
        const stmt = section.statements[i];
        if (!stmt) continue;
        if (stmt.statement_type === 'clinician_entered') {
          continue;
        }
        const isFlagged = stmt.risk_tier === 'requires_review' || stmt.risk_tier === 'red_flag';
        const isReviewed = state.statementReviews[stmt.id] === true;

        if (isFlagged) {
          const det = state.statementDeterminations[stmt.id] || '';
          if (!isReviewed || det.trim().length < 3) {
            blockingItems.push({
              itemId: stmt.id,
              reason: `Statement ${i + 1} (${secKey}): enter your own determination (at least 3 characters)`,
            });
          }
        } else {
          if (!isReviewed) {
            blockingItems.push({
              itemId: stmt.id,
              reason: `Statement ${i + 1} (${secKey}): confirm statement`,
            });
          }
        }
      }
    }
  }

  // Medication phase sections: plan + medications
  if (phase === 'medication' || phase === 'all') {
    const planSection = soapNote.sections.plan;
    if (planSection && !planSection.insufficient_content) {
      for (let i = 0; i < planSection.statements.length; i++) {
        const stmt = planSection.statements[i];
        if (!stmt) continue;
        if (stmt.statement_type === 'clinician_entered') {
          continue;
        }
        if (!state.statementReviews[stmt.id]) {
          blockingItems.push({
            itemId: stmt.id,
            reason: `Plan statement ${i + 1}: confirm statement`,
          });
        }
      }
    }

    const meds = soapNote.medications ?? [];
    for (const med of meds) {
      const isReviewed = state.statementReviews[med.id] === true;
      if (med.needs_manual_confirmation) {
        const entry = state.medicationEntries[med.id] || '';
        if (!isReviewed || entry.trim().length < 3) {
          blockingItems.push({
            itemId: med.id,
            reason: `Medication "${med.verbatim}": enter manual confirmation (at least 3 characters)`,
          });
        }
      } else {
        if (!isReviewed) {
          blockingItems.push({
            itemId: med.id,
            reason: `Medication "${med.verbatim}": confirm medication`,
          });
        }
      }

      // Check safety flags
      for (let idx = 0; idx < med.flags.length; idx++) {
        const key = `${med.id}:${idx}`;
        if (!state.flagAcknowledgments[key]) {
          blockingItems.push({
            itemId: med.id,
            reason: `Safety flag on ${med.verbatim}: ${med.flags[idx]?.message.slice(0, 60)}...`,
          });
        }
      }
    }
  }

  return {
    canSign: blockingItems.length === 0,
    blockingReasons: blockingItems.map((b) => b.reason),
    blockingItems,
  };
}

interface UseReviewStateReturn {
  reviewState: ReviewState & {
    statementDeterminations: Record<string, string>;
    medicationEntries: Record<string, string>;
  };
  isStatementReviewed: (id: string) => boolean;
  isFlagAcknowledged: (key: string) => boolean;
  reviewStatement: (id: string) => void;
  acknowledgeSafetyFlag: (key: string) => void;
  setStatementDetermination: (id: string, text: string) => void;
  setMedicationEntry: (id: string, text: string) => void;
  canSign: boolean;
  blockingReasons: string[];
  blockingItems: BlockingItem[];
}

export function useReviewState(soapNote: SoapNote | null, phase: ReviewPhase = 'all'): UseReviewStateReturn {
  const [statementReviews, setStatementReviews] = useState<Record<string, boolean>>({});
  const [flagAcknowledgments, setFlagAcknowledgments] = useState<Record<string, boolean>>({});
  const [sectionEdits] = useState<Record<string, string>>({});
  const [statementDeterminations, setStatementDeterminations] = useState<Record<string, string>>({});
  const [medicationEntries, setMedicationEntries] = useState<Record<string, string>>({});

  const isStatementReviewed = useCallback(
    (id: string) => {
      if (statementReviews[id] === true) return true;
      if (soapNote) {
        for (const secKey of ['subjective', 'objective', 'assessment', 'plan'] as const) {
          const sec = soapNote.sections[secKey];
          if (sec?.statements) {
            const found = sec.statements.find((s) => s.id === id);
            if (found?.statement_type === 'clinician_entered') {
              return true;
            }
          }
        }
      }
      return false;
    },
    [soapNote, statementReviews],
  );

  const isFlagAcknowledged = useCallback(
    (key: string) => flagAcknowledgments[key] === true,
    [flagAcknowledgments],
  );

  const reviewStatement = useCallback((id: string) => {
    setStatementReviews((prev) => ({ ...prev, [id]: true }));
  }, []);

  const acknowledgeSafetyFlag = useCallback((key: string) => {
    setFlagAcknowledgments((prev) => ({ ...prev, [key]: true }));
  }, []);

  const setStatementDetermination = useCallback((id: string, text: string) => {
    setStatementDeterminations((prev) => ({ ...prev, [id]: text }));
    if (text.trim().length >= 3) {
      setStatementReviews((prev) => ({ ...prev, [id]: true }));
    }
  }, []);

  const setMedicationEntry = useCallback((id: string, text: string) => {
    setMedicationEntries((prev) => ({ ...prev, [id]: text }));
    if (text.trim().length >= 3) {
      setStatementReviews((prev) => ({ ...prev, [id]: true }));
    }
  }, []);

  const { canSign, blockingReasons, blockingItems } = useMemo(() => {
    return computeReviewState(soapNote, phase, {
      statementReviews,
      flagAcknowledgments,
      statementDeterminations,
      medicationEntries,
    });
  }, [soapNote, phase, statementReviews, flagAcknowledgments, statementDeterminations, medicationEntries]);

  const reviewState = {
    statementReviews,
    flagAcknowledgments,
    sectionApprovals: {},
    sectionEdits,
    statementDeterminations,
    medicationEntries,
    canSign,
  };

  return {
    reviewState,
    isStatementReviewed,
    isFlagAcknowledged,
    reviewStatement,
    acknowledgeSafetyFlag,
    setStatementDetermination,
    setMedicationEntry,
    canSign,
    blockingReasons,
    blockingItems,
  };
}
