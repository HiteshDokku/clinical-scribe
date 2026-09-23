import { useState, useCallback, useMemo } from 'react';
import type { SoapNote, ReviewState } from '@/types/contracts';

interface UseReviewStateReturn {
  reviewState: ReviewState;
  isStatementReviewed: (id: string) => boolean;
  isFlagAcknowledged: (key: string) => boolean;
  reviewStatement: (id: string) => void;
  acknowledgeSafetyFlag: (key: string) => void;
  canSign: boolean;
  blockingReasons: string[];
}

/**
 * Tracks per-statement and per-safety-flag acknowledgment.
 * Sign is only enabled when ALL ungrounded statements are confirmed
 * and ALL safety flags are individually acknowledged.
 *
 * There is deliberately no "Approve All" action — per AGENTS.md prohibition.
 */
export function useReviewState(soapNote: SoapNote | null): UseReviewStateReturn {
  const [statementReviews, setStatementReviews] = useState<Record<string, boolean>>({});
  const [flagAcknowledgments, setFlagAcknowledgments] = useState<Record<string, boolean>>({});

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

  const { canSign, blockingReasons } = useMemo(() => {
    if (!soapNote) return { canSign: false, blockingReasons: ['No note loaded'] };

    const reasons: string[] = [];

    // Check ungrounded statements
    const ungroundedIds = soapNote.grounding.ungrounded_ids;
    const unconfirmedUngrounded = ungroundedIds.filter((id) => !statementReviews[id]);
    if (unconfirmedUngrounded.length > 0) {
      reasons.push(
        `${unconfirmedUngrounded.length} ungrounded statement(s) require confirmation`,
      );
    }

    // Check medication safety flags
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

    return { canSign: reasons.length === 0, blockingReasons: reasons };
  }, [soapNote, statementReviews, flagAcknowledgments]);

  const reviewState: ReviewState = {
    statementReviews,
    flagAcknowledgments,
    canSign,
  };

  return {
    reviewState,
    isStatementReviewed,
    isFlagAcknowledged,
    reviewStatement,
    acknowledgeSafetyFlag,
    canSign,
    blockingReasons,
  };
}
