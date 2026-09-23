import { motion, AnimatePresence } from 'framer-motion';
import type { ConsentState } from '@/types/contracts';

interface Props {
  consentState: ConsentState;
  onConsent: (value: ConsentState) => void;
}

export function ConsentGate({ consentState, onConsent }: Props) {
  const isBlocking = consentState === 'pending';
  const isDeclined = consentState === 'declined';

  return (
    <AnimatePresence>
      {(isBlocking || isDeclined) && (
        <motion.div
          key="consent-gate"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="absolute inset-0 z-40 flex items-center justify-center bg-surface-0/80 backdrop-blur-md rounded-2xl"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="glass-card-elevated p-8 max-w-md w-full mx-4"
          >
            {/* Shield icon */}
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 rounded-2xl bg-clinical-600/20 flex items-center justify-center">
                <svg className="w-8 h-8 text-clinical-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                </svg>
              </div>
            </div>

            <h3 className="text-lg font-bold text-white text-center mb-2">
              Patient Consent Required
            </h3>
            <p className="text-sm text-gray-400 text-center mb-6">
              Recording cannot begin until patient consent is explicitly logged.
              This is a clinical safety requirement.
            </p>

            {isDeclined && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="rounded-lg bg-safety-flag-red/10 border border-safety-flag-red/20 p-3 mb-4"
              >
                <p className="text-sm text-safety-flag-red text-center">
                  Consent was declined. Recording is not permitted.
                </p>
              </motion.div>
            )}

            <div className="space-y-3">
              <motion.button
                onClick={() => onConsent('granted')}
                className="btn-primary w-full"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Consent Granted
              </motion.button>

              <motion.button
                onClick={() => onConsent('granted_verbal_witnessed')}
                className="btn-secondary w-full"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
                </svg>
                Verbal Consent (Witnessed)
              </motion.button>

              <motion.button
                onClick={() => onConsent('declined')}
                className="btn-ghost w-full text-gray-500 hover:text-safety-flag-red"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
              >
                Declined
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
