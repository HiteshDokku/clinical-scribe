import { useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';

interface Props {
  isRecording: boolean;
  audioLevel: number;
  onStart: () => void;
  onStop: () => void;
  disabled: boolean;
}

export function AudioRecorder({ isRecording, audioLevel, onStart, onStop, disabled }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const levelsRef = useRef<number[]>(new Array(64).fill(0) as number[]);

  const drawWaveform = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);

    // Shift levels left, push new level
    levelsRef.current.shift();
    levelsRef.current.push(isRecording ? audioLevel : 0);

    const barWidth = width / levelsRef.current.length;
    const centerY = height / 2;

    for (let i = 0; i < levelsRef.current.length; i++) {
      const level = levelsRef.current[i]!;
      const barHeight = Math.max(2, level * height * 0.8);

      // Gradient from clinical blue to brighter
      const alpha = 0.3 + level * 0.7;
      ctx.fillStyle = isRecording
        ? `rgba(92, 124, 250, ${alpha})`
        : `rgba(100, 116, 139, ${alpha * 0.4})`;

      const x = i * barWidth + barWidth * 0.15;
      const w = barWidth * 0.7;
      const radius = w / 2;

      // Rounded bar
      ctx.beginPath();
      ctx.roundRect(x, centerY - barHeight / 2, w, barHeight, radius);
      ctx.fill();
    }

    animFrameRef.current = requestAnimationFrame(drawWaveform);
  }, [audioLevel, isRecording]);

  useEffect(() => {
    animFrameRef.current = requestAnimationFrame(drawWaveform);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [drawWaveform]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1, duration: 0.4 }}
      className="glass-card p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {isRecording && <div className="recording-dot" />}
          <span className="text-sm font-medium text-gray-300">
            {isRecording ? 'Recording in progress...' : 'Ready to record'}
          </span>
        </div>
      </div>

      {/* Waveform canvas */}
      <div className="relative rounded-xl bg-surface-0/50 border border-white/[0.04] overflow-hidden mb-5">
        <canvas
          ref={canvasRef}
          width={640}
          height={120}
          className="w-full h-[120px]"
        />
        {!isRecording && !disabled && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs text-gray-500">Click Start to begin recording</span>
          </div>
        )}
      </div>

      <div className="flex justify-center gap-4">
        {!isRecording ? (
          <motion.button
            onClick={onStart}
            disabled={disabled}
            className="btn-primary px-8"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
            </svg>
            Start Recording
          </motion.button>
        ) : (
          <motion.button
            onClick={onStop}
            className="btn-danger px-8"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
            Stop Recording
          </motion.button>
        )}
      </div>
    </motion.div>
  );
}
