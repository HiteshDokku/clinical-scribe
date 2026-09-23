import { useState } from 'react';
import { motion } from 'framer-motion';

interface Props {
  onStart: (clinicianId: string, patientRef: string) => void;
  isLoading: boolean;
}

export function StartEncounterForm({ onStart, isLoading }: Props) {
  const [clinicianId, setClinicianId] = useState('dr-martinez');
  const [patientRef, setPatientRef] = useState('PT-2024-0847');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (clinicianId.trim() && patientRef.trim()) {
      onStart(clinicianId.trim(), patientRef.trim());
    }
  };

  return (
    <motion.form
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="glass-card-elevated p-8 w-full max-w-lg mx-auto"
    >
      <div className="text-center mb-8">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-clinical-600/20 mb-4"
        >
          <svg className="w-8 h-8 text-clinical-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
          </svg>
        </motion.div>
        <h2 className="text-xl font-bold text-white">New Consultation</h2>
        <p className="text-sm text-gray-400 mt-1">Begin a new encounter session</p>
      </div>

      <div className="space-y-5">
        <div>
          <label htmlFor="clinician-id" className="section-label block mb-2">
            Clinician ID
          </label>
          <input
            id="clinician-id"
            type="text"
            value={clinicianId}
            onChange={(e) => setClinicianId(e.target.value)}
            className="w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 py-3 text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-clinical-500/50 focus:ring-1 focus:ring-clinical-500/30 transition-all"
            placeholder="e.g. dr-martinez"
            required
          />
        </div>

        <div>
          <label htmlFor="patient-ref" className="section-label block mb-2">
            Patient Reference
          </label>
          <input
            id="patient-ref"
            type="text"
            value={patientRef}
            onChange={(e) => setPatientRef(e.target.value)}
            className="w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 py-3 text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-clinical-500/50 focus:ring-1 focus:ring-clinical-500/30 transition-all"
            placeholder="e.g. PT-2024-0847"
            required
          />
        </div>

        <motion.button
          type="submit"
          disabled={isLoading || !clinicianId.trim() || !patientRef.trim()}
          className="btn-primary w-full mt-2"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <>
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Creating Session...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" />
              </svg>
              Start Session
            </>
          )}
        </motion.button>
      </div>

      <p className="text-xs text-gray-500 text-center mt-6">
        All data remains local. No cloud services are used.
      </p>
    </motion.form>
  );
}
