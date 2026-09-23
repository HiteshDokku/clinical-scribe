import { useState, useRef, useCallback } from 'react';

interface UseAudioCaptureReturn {
  isRecording: boolean;
  audioLevel: number;
  start: () => Promise<void>;
  stop: () => void;
  /** Register a handler to receive PCM chunks */
  onChunk: (handler: (chunk: ArrayBuffer) => void) => void;
}

/**
 * Web Audio API capture hook.
 * Opens getUserMedia, creates a 16 kHz mono AudioContext,
 * and produces raw PCM16 chunks via ScriptProcessorNode.
 */
export function useAudioCapture(): UseAudioCaptureReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  const contextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const chunkHandlerRef = useRef<((chunk: ArrayBuffer) => void) | null>(null);

  const start = useCallback(async () => {
    try {
      console.log('[Audio] Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      console.log('[Audio] Microphone access granted.');
      streamRef.current = stream;

      const ctx = new AudioContext({ sampleRate: 16000 });
      contextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);

      // ScriptProcessorNode for chunk-level access
      // Buffer size 4096 samples at 16kHz = ~256ms chunks
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);

        // Compute RMS level for visualisation
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i]! * inputData[i]!;
        }
        const rms = Math.sqrt(sum / inputData.length);
        setAudioLevel(Math.min(1, rms * 5));

        // Convert Float32 to Int16 PCM
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]!));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        chunkHandlerRef.current?.(pcm16.buffer);
      };

      source.connect(processor);
      processor.connect(ctx.destination);

      setIsRecording(true);
    } catch (err) {
      console.error('[Audio] Microphone access denied or failed:', err);
      throw err;
    }
  }, []);

  const stop = useCallback(() => {
    processorRef.current?.disconnect();
    contextRef.current?.close();
    streamRef.current?.getTracks().forEach((t) => t.stop());

    processorRef.current = null;
    contextRef.current = null;
    streamRef.current = null;

    setIsRecording(false);
    setAudioLevel(0);
  }, []);

  const onChunk = useCallback((handler: (chunk: ArrayBuffer) => void) => {
    chunkHandlerRef.current = handler;
  }, []);

  return { isRecording, audioLevel, start, stop, onChunk };
}
