import { useState } from 'react';
import { motion } from 'framer-motion';
import type { Medication } from '@/types/contracts';
import { SafetyFlagBadge } from './SafetyFlagBadge';

interface Props {
  medication: Medication;
  isFlagAcknowledged: (key: string) => boolean;
  onAcknowledgeFlag: (key: string) => void;
  onManualEntry?: (id: string, text: string) => void;
  manualEntry?: string;
  isReviewed?: boolean;
  onReview?: (id: string) => void;
  serverError?: string;
}

export function MedicationRow({
  medication,
  isFlagAcknowledged,
  onAcknowledgeFlag,
  onManualEntry,
  manualEntry,
  isReviewed = false,
  onReview,
  serverError,
}: Props) {
  const hasFlags = medication.flags.length > 0;
  const [typedMedication, setTypedMedication] = useState(manualEntry || '');
  const [isEditing, setIsEditing] = useState(false);

  const isConfirmed = isReviewed || !!manualEntry;

  const handleManualConfirm = () => {
    if (typedMedication.trim().length >= 3 && onManualEntry) {
      onManualEntry(medication.id, typedMedication.trim());
      if (onReview) onReview(medication.id);
      setIsEditing(false);
    }
  };

  const handleStandardConfirm = () => {
    if (onReview) {
      onReview(medication.id);
    }
  };

  return (
    <motion.div
      id={`item-${medication.id}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      data-testid={`medication-${medication.id}`}
      className={`rounded-xl border p-4 transition-all ${
        hasFlags || medication.needs_manual_confirmation
          ? 'border-safety-flag-amber/20 bg-safety-flag-amber/[0.02]'
          : 'border-white/[0.06] bg-white/[0.02]'
      }`}
    >
      {/* Inline server error display */}
      {serverError && (
        <div className="mb-3 p-2.5 rounded-lg bg-red-950/80 border border-red-500/50 text-red-200 text-xs flex items-center gap-2" role="alert">
          <svg className="w-4 h-4 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{serverError}</span>
        </div>
      )}

      <div className="flex items-center gap-3 mb-3">
        <span className="text-lg">💊</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-semibold text-white">
              {medication.needs_manual_confirmation ? "Reference: " + medication.verbatim : medication.verbatim}
            </h4>
            <span className="badge-ai text-[10px]">AI-drafted</span>
            {medication.needs_manual_confirmation && (
              <span className="badge-warning text-[10px]">Manual confirm needed</span>
            )}
            {isConfirmed && (
              <span className="badge-success text-[10px] flex items-center gap-1">
                <svg className="w-3 h-3 text-safety-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Confirmed
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
            {medication.dose && (
              <span>{medication.dose.value}{medication.dose.unit}</span>
            )}
            {medication.frequency && <span>· {medication.frequency}</span>}
            {medication.route && <span>· {medication.route}</span>}
            {medication.ingredient_id && (
              <span className="font-mono text-[10px] text-gray-500">
                [{medication.ingredient_id}]
              </span>
            )}
          </div>
        </div>

        {!medication.needs_manual_confirmation && (
          <div className="shrink-0">
            {!isConfirmed ? (
              <button
                onClick={handleStandardConfirm}
                className="btn-primary text-xs px-3 py-1.5"
                title="Confirm medication"
                data-testid={`confirm-med-${medication.id}`}
              >
                Confirm
              </button>
            ) : (
              <span className="text-xs text-safety-success font-medium">Confirmed ✓</span>
            )}
          </div>
        )}
      </div>

      {medication.needs_manual_confirmation && (
        <div className="mt-4 p-3 bg-clinical-900/50 rounded-lg border border-amber-500/20">
          <p className="text-xs text-amber-300 mb-2 font-medium">
            Please manually confirm medication details (e.g., dose and frequency) before approving.
          </p>
          {isConfirmed && !isEditing ? (
            <div>
              <div className="bg-white/5 p-3 rounded-lg text-sm text-gray-200">
                {manualEntry || typedMedication}
              </div>
              <div className="mt-2 flex justify-end">
                <button
                  onClick={() => setIsEditing(true)}
                  className="btn-ghost text-xs px-2.5 py-1"
                >
                  Edit
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <input
                type="text"
                value={typedMedication}
                onChange={(e) => setTypedMedication(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    if (typedMedication.trim().length >= 3) {
                      handleManualConfirm();
                    }
                  }
                }}
                className="w-full bg-clinical-900 border border-amber-500/40 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-amber-400"
                placeholder="Type medication, dose, route, and frequency..."
                aria-describedby={`med-hint-${medication.id}`}
              />
              <div className="flex items-center justify-between mt-1">
                <span id={`med-hint-${medication.id}`} className="text-[11px] text-gray-400">
                  Ctrl+Enter to confirm (min 3 chars)
                </span>
                <div className="flex items-center gap-2">
                  {isEditing && (
                    <button
                      onClick={() => setIsEditing(false)}
                      className="btn-ghost text-xs px-3 py-1.5"
                    >
                      Cancel
                    </button>
                  )}
                  <button
                    disabled={typedMedication.trim().length < 3}
                    title={typedMedication.trim().length < 3 ? "Medication entry must contain at least 3 characters" : "Confirm medication entry"}
                    aria-describedby={`med-hint-${medication.id}`}
                    onClick={handleManualConfirm}
                    className="bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg px-4 py-1.5 text-xs font-semibold transition-all"
                    data-testid={`confirm-btn-${medication.id}`}
                  >
                    Confirm
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Safety flags — rendered inline next to the drug */}
      {hasFlags && (
        <div className="space-y-2 mt-3">
          {medication.flags.map((flag, idx) => {
            const key = `${medication.id}:${idx}`;
            return (
              <SafetyFlagBadge
                key={key}
                flag={flag}
                flagKey={key}
                isAcknowledged={isFlagAcknowledged(key)}
                onAcknowledge={onAcknowledgeFlag}
              />
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
