import type { TranscriptEvent } from '@/types/contracts';

/**
 * Simulated transcript events for the recording flow demo.
 * Each event has a delay (ms) from the previous one for staggered playback.
 */
export interface TimedTranscriptEvent {
  delay: number;
  event: TranscriptEvent;
}

export const MOCK_TRANSCRIPT_SEQUENCE: TimedTranscriptEvent[] = [
  {
    delay: 800,
    event: {
      type: 'partial',
      text: 'I have been having this',
      start_ms: 0,
      end_ms: 1500,
      confidence: 0.7,
      speaker: 'patient',
    },
  },
  {
    delay: 1200,
    event: {
      type: 'final',
      text: 'I have been having this tightness in my chest for about three days now.',
      start_ms: 0,
      end_ms: 4200,
      confidence: 0.94,
      speaker: 'patient',
    },
  },
  {
    delay: 600,
    event: {
      type: 'partial',
      text: 'It gets worse when I',
      start_ms: 4500,
      end_ms: 5800,
      confidence: 0.65,
      speaker: 'patient',
    },
  },
  {
    delay: 1400,
    event: {
      type: 'final',
      text: 'It gets worse when I climb stairs or walk for a long time.',
      start_ms: 4500,
      end_ms: 7800,
      confidence: 0.91,
      speaker: 'patient',
    },
  },
  {
    delay: 1000,
    event: {
      type: 'partial',
      text: 'Do you have any pain',
      start_ms: 8500,
      end_ms: 9800,
      confidence: 0.72,
      speaker: 'clinician',
    },
  },
  {
    delay: 1200,
    event: {
      type: 'final',
      text: 'Do you have any pain going down your arm or into your jaw?',
      start_ms: 8500,
      end_ms: 12000,
      confidence: 0.93,
      speaker: 'clinician',
    },
  },
  {
    delay: 800,
    event: {
      type: 'final',
      text: 'No, I don\'t have any pain going down my arm or into my jaw.',
      start_ms: 12500,
      end_ms: 16200,
      confidence: 0.91,
      speaker: 'patient',
    },
  },
  {
    delay: 1500,
    event: {
      type: 'partial',
      text: 'Sometimes when I get up',
      start_ms: 17000,
      end_ms: 18500,
      confidence: 0.68,
      speaker: 'patient',
    },
  },
  {
    delay: 1300,
    event: {
      type: 'final',
      text: 'Sometimes when I get up in the morning I feel dizzy for a few seconds.',
      start_ms: 17000,
      end_ms: 21500,
      confidence: 0.88,
      speaker: 'patient',
    },
  },
  {
    delay: 1000,
    event: {
      type: 'final',
      text: 'Blood pressure is reading 148 over 92.',
      start_ms: 23000,
      end_ms: 26000,
      confidence: 0.97,
      speaker: 'clinician',
    },
  },
  {
    delay: 800,
    event: {
      type: 'final',
      text: 'Heart rate 88, respiratory rate 18.',
      start_ms: 26500,
      end_ms: 29000,
      confidence: 0.96,
      speaker: 'clinician',
    },
  },
  {
    delay: 1200,
    event: {
      type: 'final',
      text: 'I can hear a systolic murmur at the apex, sounds like a grade two out of six.',
      start_ms: 30000,
      end_ms: 35000,
      confidence: 0.85,
      speaker: 'clinician',
    },
  },
  {
    delay: 900,
    event: {
      type: 'final',
      text: 'Let us start you on Lisinopril, ten milligrams once a day.',
      start_ms: 36500,
      end_ms: 40200,
      confidence: 0.95,
      speaker: 'clinician',
    },
  },
  {
    delay: 1100,
    event: {
      type: 'final',
      text: 'Continue taking the Metformin five hundred milligrams twice a day as you have been.',
      start_ms: 41000,
      end_ms: 46000,
      confidence: 0.93,
      speaker: 'clinician',
    },
  },
];
