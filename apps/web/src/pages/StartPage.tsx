import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { StartEncounterForm } from '@/components/consultation/StartEncounterForm';
import { useEncounter } from '@/hooks/useEncounter';

export function StartPage() {
  const navigate = useNavigate();
  const { isLoading, createEncounter } = useEncounter();

  const handleStart = async (clinicianId: string, patientRef: string) => {
    try {
      const enc = await createEncounter(clinicianId, patientRef);
      navigate(`/encounter/${enc.id}`);
    } catch {
      // Error is displayed via the hook
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      {/* Background gradient orbs */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-clinical-600/[0.08] blur-[100px]" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-clinical-700/[0.06] blur-[100px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center mb-10"
      >
        <h1 className="text-3xl font-extrabold gradient-text mb-2">
          Clinical Scribe
        </h1>
        <p className="text-sm text-gray-400 max-w-md">
          Privacy-preserving AI-assisted clinical documentation.
          All data remains local — no cloud services.
        </p>
      </motion.div>

      <StartEncounterForm onStart={handleStart} isLoading={isLoading} />

      {/* Quick link to review demo */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
        className="mt-8"
      >
        <button
          onClick={() => navigate('/encounter/mock-encounter-001/review')}
          className="btn-ghost text-xs text-gray-500"
        >
          Skip to SOAP Review Demo →
        </button>
      </motion.div>
    </div>
  );
}
