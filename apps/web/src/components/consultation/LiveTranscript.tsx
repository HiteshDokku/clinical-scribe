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

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.4 }}
      className="bg-surface-2 rounded-xl p-6 flex flex-col shadow-sm border border-surface-3"
      style={{ minHeight: '400px' }}
    >
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-4 max-h-[500px] pr-2"
      >
        {segments.length === 0 && !currentPartial && (
          <div className="flex items-center justify-center h-full min-h-[250px]">
            <p className="text-sm text-gray-400 italic">
              Transcript will appear here as you speak...
            </p>
          </div>
        )}

        <AnimatePresence mode="popLayout">
          {segments.map((seg) => {
            return (
              <motion.div
                key={seg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="flex flex-col w-full justify-start border-l-4 border-slate-700 pl-4 py-2"
              >
                <div className="flex items-center gap-3 mb-1.5">

                  <span className="text-[11px] text-gray-400 font-mono">
                    {formatTime(seg.start_ms)} – {formatTime(seg.end_ms)}
                  </span>
                  <span className="ml-auto text-[10px] text-gray-400 font-mono uppercase tracking-wider" title="ASR Transcription Confidence">
                    ASR: {(seg.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-gray-200 font-mono text-sm leading-relaxed">{seg.text}</p>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Partial (in-progress) segment */}
        <AnimatePresence>
          {currentPartial && (
            <motion.div
              key="partial"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col w-full justify-start border-l-4 border-slate-700 pl-4 py-2 opacity-50"
            >
              <div className="flex items-center gap-3 mb-1.5">
                <div className="flex gap-0.5 ml-1 opacity-50">
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
              <p className="text-gray-400 font-mono text-sm italic leading-relaxed">{currentPartial.text}</p>
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
