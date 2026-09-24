import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { TranscriptSegment } from '@/hooks/useTranscript';

interface Props {
  segments: TranscriptSegment[];
  currentPartial: TranscriptSegment | null;
}

export function LiveTranscript({ segments, currentPartial }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new segments
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [segments, currentPartial]);

  const getSpeakerColor = (speaker?: string | null) => {
    if (speaker === 'clinician') return 'text-clinical-300';
    if (speaker === 'patient') return 'text-emerald-400';
    return 'text-gray-400';
  };

  const getSpeakerLabel = (speaker?: string | null) => {
    if (speaker === 'clinician') return '[Doctor]';
    if (speaker === 'patient') return '[Patient]';
    return '[Unknown]';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.4 }}
      className="glass-card p-6 flex flex-col"
      style={{ minHeight: '320px' }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-label">Live Transcript</h3>
        <span className="text-xs text-gray-500">
          {segments.length} segment{segments.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-3 max-h-[400px] pr-2"
      >
        {segments.length === 0 && !currentPartial && (
          <div className="flex items-center justify-center h-full min-h-[200px]">
            <p className="text-sm text-gray-500 italic">
              Transcript will appear here as you speak...
            </p>
          </div>
        )}

        <AnimatePresence mode="popLayout">
          {segments.map((seg) => (
            <motion.div
              key={seg.id}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="rounded-lg bg-white/[0.02] border border-white/[0.04] p-3"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-semibold ${getSpeakerColor(seg.speaker)}`}>
                  {getSpeakerLabel(seg.speaker)}
                </span>
                <span className="text-[10px] text-gray-600 font-mono">
                  {formatTime(seg.start_ms)} – {formatTime(seg.end_ms)}
                </span>
                <span className="ml-auto text-[10px] text-gray-600">
                  {(seg.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-sm text-gray-200 leading-relaxed">{seg.text}</p>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Partial (in-progress) segment */}
        <AnimatePresence>
          {currentPartial && (
            <motion.div
              key="partial"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2 }}
              className="rounded-lg border border-clinical-500/20 bg-clinical-600/[0.05] p-3"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-semibold ${getSpeakerColor(currentPartial.speaker)}`}>
                  {getSpeakerLabel(currentPartial.speaker)}
                </span>
                <div className="flex gap-0.5 ml-1">
                  <span className="w-1 h-1 rounded-full bg-clinical-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1 h-1 rounded-full bg-clinical-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1 h-1 rounded-full bg-clinical-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
              <p className="text-sm text-gray-300 italic">{currentPartial.text}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}
