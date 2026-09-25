import { useState, useCallback, useMemo } from 'react';
import type { SoapNote, ReviewState } from '@/types/contracts';

interface UseReviewStateReturn {
  reviewState: ReviewState;
  isStatementReviewed: (id: string) => boolean;
  isFlagAcknowledged: (key: string) => boolean;
  reviewStatement: (id: string) => void;
  acknowledgeSafetyFlag: (key: string) => void;
  approveSection: (key: string, text?: string) => void;
  canSign: boolean;
  blockingReasons: string[];
}

/**
 * Tracks per-statement and per-safety-flag acknowledgment, and per-section approvals.
 * Sign is only enabled when all sections are approved, all ungrounded statements in non-edited sections are confirmed,
 * and all safety flags in non-edited medications section are individually acknowledged.
 */
export function useReviewState(soapNote: SoapNote | null): UseReviewStateReturn {
  const [statementReviews, setStatementReviews] = useState<Record<string, boolean>>({});
  const [flagAcknowledgments, setFlagAcknowledgments] = useState<Record<string, boolean>>({});
  const [sectionApprovals, setSectionApprovals] = useState<Record<string, boolean>>({});
  const [sectionEdits, setSectionEdits] = useState<Record<string, string>>({});

  const isStatementReviewed = useCallback(
    (id: string) => statementReviews[id] === true,
    [statementReviews],
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

  const approveSection = useCallback((key: string, text?: string) => {
    setSectionApprovals((prev) => ({ ...prev, [key]: true }));
    if (text !== undefined) {
      setSectionEdits((prev) => ({ ...prev, [key]: text }));
    }
  }, []);

  const { canSign, blockingReasons } = useMemo(() => {
    if (!soapNote) return { canSign: false, blockingReasons: ['No note loaded'] };

    const reasons: string[] = [];
    
    // Check section approvals
    const sections = ['subjective', 'objective', 'assessment', 'plan'];
    if (soapNote.medications && soapNote.medications.length > 0) {
      sections.push('medications');
    }
    
    for (const sec of sections) {
      if (!sectionApprovals[sec]) {
        reasons.push(`${sec.charAt(0).toUpperCase() + sec.slice(1)} section requires approval`);
      }
    }

    // Identify statements that belong to edited sections, because they shouldn't block
    const editedStatementIds = new Set<string>();
    for (const sec of ['subjective', 'objective', 'assessment', 'plan']) {
      if (sectionEdits[sec] !== undefined) {
        const statements = soapNote.sections[sec as keyof typeof soapNote.sections] || [];
        statements.forEach(s => editedStatementIds.add(s.id));
      }
    }

    // Check ungrounded statements (skip if section is edited)
    const ungroundedIds = soapNote.grounding.ungrounded_ids;
    const unconfirmedUngrounded = ungroundedIds.filter((id) => !statementReviews[id] && !editedStatementIds.has(id));
    if (unconfirmedUngrounded.length > 0) {
      reasons.push(
        `${unconfirmedUngrounded.length} ungrounded statement(s) require confirmation`,
      );
    }

    // Check medication safety flags (skip if medications section is edited)
    if (sectionEdits['medications'] === undefined) {
      const meds = soapNote.medications ?? [];
      for (const med of meds) {
        for (let i = 0; i < med.flags.length; i++) {
          const key = `${med.id}:${i}`;
          if (!flagAcknowledgments[key]) {
            reasons.push(
              `Safety flag on ${med.verbatim}: ${med.flags[i]!.message.slice(0, 60)}...`,
            );
          }
        }
      }
    }

    return { canSign: reasons.length === 0, blockingReasons: reasons };
  }, [soapNote, statementReviews, flagAcknowledgments, sectionApprovals, sectionEdits]);

  const reviewState: ReviewState = {
    statementReviews,
    flagAcknowledgments,
    sectionApprovals,
    sectionEdits,
    canSign,
  };

  return {
    reviewState,
    isStatementReviewed,
    isFlagAcknowledged,
    reviewStatement,
    acknowledgeSafetyFlag,
    approveSection,
    canSign,
    blockingReasons,
  };
}
