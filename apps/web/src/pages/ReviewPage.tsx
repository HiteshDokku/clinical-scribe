import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { SoapReviewScreen } from '@/components/review/SoapReviewScreen';
import { getEncounter, signNote, confirmDiagnosis } from '@/api/encounters';
import type { ReviewPhase } from '@/hooks/useReviewState';

export function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [encounterState, setEncounterState] = useState<string>('');
  const [liveNote, setLiveNote] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [transcript, setTranscript] = useState<any[]>([]);

  useEffect(() => {
    if (!id) return;
    let mounted = true;
    getEncounter(id)
      .then((data) => {
        if (mounted) {
          console.log("DEBUG FRONTEND PAYLOAD:", data);
          setLiveNote(data.note);
          setEncounterState(data.state);
          setTranscript(data.transcript || []);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message);
          setIsLoading(false);
        }
      });
    return () => { mounted = false; };
  }, [id]);

  const soapNote = liveNote;
  
  // Extract transcript and build the evidence map
  const evidenceMap: Record<string, string> = {};
  for (const segment of transcript) {
    evidenceMap[segment.id] = segment.text;
  }

  const handleSign = useCallback(async (editedSections: Record<string, string>) => {
    if (!id) return;
    setIsSubmitting(true);
    try {
      if (encounterState === 'diagnosis_review') {
        const confirmedText = editedSections.assessment || soapNote?.sections.assessment.statements.map((s: any) => s.text).join('\n') || '';
        await confirmDiagnosis(id, confirmedText);
        // fetch encounter again to get the new state
        const data = await getEncounter(id);
        setLiveNote(data.note);
        setEncounterState(data.state);
      } else {
        await signNote(id, editedSections);
        setEncounterState('signed');
      }
    } catch (err) {
      console.error('Failed to process:', err);
      alert('Failed to process request: ' + (err instanceof Error ? err.message : 'Internal Server Error'));
    } finally {
      setIsSubmitting(false);
    }
  }, [id, encounterState, soapNote]);

  const reviewPhase: ReviewPhase = encounterState === 'diagnosis_review' ? 'diagnosis' : encounterState === 'medication_review' ? 'medication' : 'all';

  return (
    <div className="min-h-screen p-4 md:p-8 max-w-3xl mx-auto">
      {/* Background gradient */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-0 left-1/3 w-72 h-72 rounded-full bg-clinical-600/[0.05] blur-[100px]" />
        <div className="absolute bottom-1/4 right-0 w-80 h-80 rounded-full bg-clinical-800/[0.04] blur-[100px]" />
      </div>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <button onClick={() => navigate(`/encounter/${id}`)} className="btn-ghost">
          ← Back to Consultation
        </button>
        <button onClick={() => navigate('/')} className="btn-ghost">
          New Session
        </button>
      </motion.div>

      <AnimatePresence mode="wait">
        {isLoading ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20"
          >
            <div className="w-12 h-12 border-4 border-clinical-500/30 border-t-clinical-500 rounded-full animate-spin mb-4" />
            <p className="text-gray-400">Loading clinical note...</p>
          </motion.div>
        ) : error ? (
          <motion.div
            key="error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="glass-card-elevated p-8 text-center text-safety-error"
          >
            <p>{error}</p>
          </motion.div>
        ) : encounterState !== 'signed' ? (
          <motion.div
            key={`review-${encounterState}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div data-testid="debug-phase" className="text-white">PHASE: {reviewPhase} STATE: {encounterState}</div>
            <SoapReviewScreen
              soapNote={soapNote}
              evidenceMap={evidenceMap}
              onSign={handleSign}
              phase={reviewPhase}
              isSubmitting={isSubmitting}
            />
          </motion.div>
        ) : (
          <motion.div
            key="signed"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card-elevated p-12 text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
              className="w-20 h-20 rounded-full bg-safety-success/20 flex items-center justify-center mx-auto mb-6"
            >
              <svg className="w-10 h-10 text-safety-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </motion.div>
            <h2 className="text-2xl font-bold text-white mb-2">Note Signed Successfully</h2>
            <p className="text-sm text-gray-400 mb-6">
              The clinical note has been signed and submitted for processing.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button onClick={() => navigate('/')} className="btn-primary">
                Start New Session
              </button>
              <button onClick={() => navigate(`/audit/${id}`)} className="btn-secondary">
                View Audit Log
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
