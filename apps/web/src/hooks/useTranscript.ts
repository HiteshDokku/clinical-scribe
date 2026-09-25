import { useState, useCallback } from 'react';
import type { TranscriptEvent } from '@/types/contracts';

export interface TranscriptSegment {
  id: string;
  text: string;
  type: 'partial' | 'final';
  speaker?: string | null;
  confidence: number;
  start_ms: number;
  end_ms: number;
}

interface UseTranscriptReturn {
  segments: TranscriptSegment[];
  currentPartial: TranscriptSegment | null;
  addEvent: (event: TranscriptEvent) => void;
  clear: () => void;
}

let segmentCounter = 0;

/**
 * Accumulates transcript events into a displayable list.
 * Partial events replace each other; final events are appended permanently.
 */
export function useTranscript(): UseTranscriptReturn {
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [currentPartial, setCurrentPartial] = useState<TranscriptSegment | null>(null);

  const addEvent = useCallback((event: TranscriptEvent) => {
    const segment: TranscriptSegment = {
      id: event.id || `seg-${++segmentCounter}`,
      text: event.text,
      type: event.type,
      speaker: event.speaker,
      confidence: event.confidence,
      start_ms: event.start_ms,
      end_ms: event.end_ms,
    };

    if (event.type === 'partial') {
      setCurrentPartial(segment);
    } else {
      setCurrentPartial(null);
      setSegments((prev) => {
        // If we receive an event with the same ID, replace it (used for swap)
        const idx = prev.findIndex((s) => s.id === segment.id);
        if (idx !== -1) {
          const next = [...prev];
          next[idx] = segment;
          return next;
        }
        return [...prev, segment];
      });
    }
  }, []);

  const clear = useCallback(() => {
    setSegments([]);
    setCurrentPartial(null);
  }, []);

  return { segments, currentPartial, addEvent, clear };
}
