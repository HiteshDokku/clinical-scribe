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

  const getSpeakerStyles = (speaker?: string | null) => {
    if (speaker === 'clinician') {
      return {
        container: 'flex w-full justify-start',
        bubble: 'bg-clinical-900/30 border-clinical-500/30 rounded-br-2xl rounded-tr-2xl rounded-tl-2xl rounded-bl-sm',
        text: 'text-clinical-100',
        label: 'text-clinical-400',
        name: 'Doctor'
      };
    }
    if (speaker === 'patient') {
      return {
        container: 'flex w-full justify-end',
        bubble: 'bg-emerald-900/30 border-emerald-500/30 rounded-bl-2xl rounded-tl-2xl rounded-tr-2xl rounded-br-sm',
        text: 'text-emerald-50',
        label: 'text-emerald-400',
        name: 'Patient'
      };
    }
    return {
      container: 'flex w-full justify-center',
      bubble: 'bg-gray-800/50 border-gray-600/50 rounded-2xl',
      text: 'text-gray-300',
      label: 'text-gray-400',
      name: 'Unknown'
    };
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.4 }}
      className="glass-card p-6 flex flex-col"
      style={{ minHeight: '400px' }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-label">Live Transcript</h3>
        <span className="text-xs text-gray-500">
          {segments.length} segment{segments.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-4 max-h-[500px] pr-2"
      >
        {segments.length === 0 && !currentPartial && (
          <div className="flex items-center justify-center h-full min-h-[250px]">
            <p className="text-sm text-gray-500 italic">
              Transcript will appear here as you speak...
            </p>
          </div>
        )}

        <AnimatePresence mode="popLayout">
          {segments.map((seg) => {
            const styles = getSpeakerStyles(seg.speaker);
            return (
              <motion.div
                key={seg.id}
                initial={{ opacity: 0, y: 12, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className={styles.container}
              >
                <div className={`max-w-[85%] p-4 border ${styles.bubble} shadow-sm`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs font-bold ${styles.label}`}>
                      {styles.name}
                    </span>
                    <span className="text-[10px] text-gray-500 font-mono">
                      {formatTime(seg.start_ms)} – {formatTime(seg.end_ms)}
                    </span>
                    <span className="ml-auto text-[10px] text-gray-500">
                      {(seg.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className={`text-sm leading-relaxed ${styles.text}`}>{seg.text}</p>
                </div>
              </motion.div>
            );
          })}
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
              className={getSpeakerStyles(currentPartial.speaker).container}
            >
              <div className={`max-w-[85%] p-4 border ${getSpeakerStyles(currentPartial.speaker).bubble} opacity-80 border-dashed`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-xs font-bold ${getSpeakerStyles(currentPartial.speaker).label}`}>
                    {getSpeakerStyles(currentPartial.speaker).name}
                  </span>
                  <div className="flex gap-0.5 ml-1">
                    <span className="w-1 h-1 rounded-full bg-clinical-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1 h-1 rounded-full bg-clinical-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1 h-1 rounded-full bg-clinical-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
                <p className={`text-sm italic ${getSpeakerStyles(currentPartial.speaker).text}`}>{currentPartial.text}</p>
              </div>
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
