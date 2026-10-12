import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import type { EncounterState } from '@/types/contracts';

interface Props {
  state: EncounterState;
  isConnected: boolean;
}

const STATE_LABELS: Record<EncounterState, string> = {
  created: 'Session Created',
  consented: 'Conversation Recorded',
  recording: 'Recording',
  transcribing: 'Processing Transcript',
  drafting: 'Generating Note',
  ready: 'Note Ready for Review',
  signed: 'Signed & Submitted',
  degraded: 'Degraded',
  cancelled: 'Cancelled',
};

export function RecordingStatusBar({ state, isConnected }: Props) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (state !== 'recording') return;
    const start = Date.now();
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [state]);

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card px-5 py-3 flex items-center justify-between"
    >
      <div className="flex items-center gap-3">
        {state === 'recording' && <div className="recording-dot" />}
        <span className="text-sm font-medium text-gray-200">
          {STATE_LABELS[state]}
        </span>
        {state === 'recording' && (
          <span className="text-sm font-mono text-gray-400">
            {formatElapsed(elapsed)}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${
            state === 'recording'
              ? (isConnected ? 'bg-safety-success' : 'bg-safety-flag-red')
              : 'bg-gray-500'
          }`}
        />
        <span className="text-xs text-gray-400">
          {state === 'recording'
            ? (isConnected ? 'Connected' : 'Disconnected')
            : 'Not recording'}
        </span>
      </div>
    </motion.div>
  );
}
