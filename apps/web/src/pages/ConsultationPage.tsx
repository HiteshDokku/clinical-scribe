import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { ConsentState, TranscriptEvent } from '@/types/contracts';
import { ConsentGate } from '@/components/consultation/ConsentGate';
import { AudioRecorder } from '@/components/consultation/AudioRecorder';
import { LiveTranscript } from '@/components/consultation/LiveTranscript';
import { RecordingStatusBar } from '@/components/consultation/RecordingStatusBar';
import { useEncounter } from '@/hooks/useEncounter';
import { useAudioCapture } from '@/hooks/useAudioCapture';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useTranscript } from '@/hooks/useTranscript';
import { IS_MOCK, mockTranscriptStream } from '@/mocks/handlers';
import { generateNote } from '@/api/encounters';

export function ConsultationPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { encounter, updateEncounter, initEncounter } = useEncounter();
  const { isRecording, audioLevel, start: startAudio, stop: stopAudio, onChunk } = useAudioCapture();
  const { isConnected, connect, sendConsent, sendAudio, sendStop } = useWebSocket();
  const { segments, currentPartial, addEvent } = useTranscript();
  const [mockCleanup, setMockCleanup] = useState<(() => void) | null>(null);

  // Derive consent/state from encounter or use local defaults for mock
  const consentState = encounter?.consent_state ?? 'pending';
  const encounterState = encounter?.state ?? 'created';

  // Initialize — set up encounter state for display
  useEffect(() => {
    if (!encounter && id) {
      // When navigating directly, set up a minimal encounter
      initEncounter(id);
    }
  }, [id, encounter, initEncounter]);

  // Connect WebSocket (non-mock only)
  useEffect(() => {
    if (!IS_MOCK && id) {
      connect(id, addEvent);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Forward audio chunks to WebSocket
  useEffect(() => {
    if (IS_MOCK) return;
    onChunk((chunk) => {
      sendAudio(chunk);
    });
  }, [onChunk, sendAudio]);

  const handleConsent = useCallback(
    (value: ConsentState) => {
      if (value === 'granted' || value === 'granted_verbal_witnessed') {
        updateEncounter({ consent_state: value, state: 'consented' });
        if (!IS_MOCK) {
          sendConsent(value);
        }
      } else {
        updateEncounter({ consent_state: value });
      }
    },
    [updateEncounter, sendConsent],
  );

  const handleStartRecording = useCallback(async () => {
    updateEncounter({ state: 'recording' });
    if (IS_MOCK) {
      // Start mock transcript stream
      const cleanup = mockTranscriptStream(
        (event: TranscriptEvent) => addEvent(event),
        () => {
          updateEncounter({ state: 'transcribing' });
          setIsStopping(true);
        },
      );
      setMockCleanup(() => cleanup);
    } else {
      await startAudio();
    }
  }, [updateEncounter, id, navigate, addEvent, startAudio]);

  const [isStopping, setIsStopping] = useState(false);

  const handleStopRecording = useCallback(async () => {
    updateEncounter({ state: 'transcribing' });
    if (IS_MOCK) {
      mockCleanup?.();
      setIsStopping(true);
    } else {
      stopAudio();
      setIsStopping(true);
      sendStop();
    }
  }, [updateEncounter, id, mockCleanup, stopAudio, sendStop]);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isNoteGenerated, setIsNoteGenerated] = useState(false);

  const handleGenerateNote = async () => {
    if (!id) return;
    setIsGenerating(true);
    try {
      const finalSegments = [...segments];
      if (currentPartial) {
        finalSegments.push(currentPartial);
      }
      
      await generateNote(id, finalSegments);
      setIsGenerating(false);
      setIsNoteGenerated(true);
    } catch (err) {
      console.error('Failed to generate note:', err);
      updateEncounter({ state: 'degraded' });
      setIsGenerating(false);
    }
  };

  const canRecord =
    consentState === 'granted' || consentState === 'granted_verbal_witnessed';

  return (
    <div className="min-h-screen p-4 md:p-8 max-w-4xl mx-auto">
      {/* Background gradient */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-1/4 right-0 w-96 h-96 rounded-full bg-clinical-600/[0.06] blur-[120px]" />
        <div className="absolute bottom-0 left-1/4 w-64 h-64 rounded-full bg-clinical-800/[0.05] blur-[80px]" />
      </div>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <div>
          <h1 className="text-xl font-bold text-white">Active Consultation</h1>
          <p className="text-xs text-gray-400 font-mono">Encounter: {id}</p>
        </div>
        <button onClick={() => navigate('/')} className="btn-ghost">
          ← Back
        </button>
      </motion.div>

      {/* Status bar */}
      <div className="mb-6">
        <RecordingStatusBar
          state={encounterState}
          isConnected={IS_MOCK || isConnected}
        />
      </div>

      {/* Main content area with consent gate overlay */}
      <div className="relative space-y-6">
        <ConsentGate
          consentState={consentState}
          onConsent={handleConsent}
        />

        <AudioRecorder
          isRecording={isRecording || encounterState === 'recording'}
          audioLevel={audioLevel}
          onStart={handleStartRecording}
          onStop={handleStopRecording}
          disabled={!canRecord}
        />

        <LiveTranscript
          segments={segments}
          currentPartial={currentPartial}
        />

        {encounterState === 'transcribing' && isConnected && !IS_MOCK && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-card p-6 text-center"
          >
            <div className="flex justify-center mb-3">
              <svg className="animate-spin w-6 h-6 text-clinical-400" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <p className="text-sm text-gray-300">Processing final audio chunks...</p>
          </motion.div>
        )}

        {isStopping && (!isConnected || IS_MOCK) && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-center mt-6"
          >
            {!isNoteGenerated ? (
              <button 
                className="px-6 py-3 rounded-lg font-semibold text-white transition-all bg-clinical-500 hover:bg-clinical-400 shadow-[0_0_20px_rgba(30,190,165,0.3)] hover:shadow-[0_0_30px_rgba(30,190,165,0.5)] flex items-center gap-2"
                onClick={handleGenerateNote}
                disabled={isGenerating}
              >
                {isGenerating ? (
                  <>
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Generating SOAP Note...
                  </>
                ) : (
                  'Generate SOAP Note'
                )}
              </button>
            ) : (
              <button 
                className="px-6 py-3 rounded-lg font-semibold text-white transition-all bg-emerald-500 hover:bg-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)] flex items-center gap-2"
                onClick={() => navigate(`/encounter/${id}/review`)}
              >
                Open SOAP Note →
              </button>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
