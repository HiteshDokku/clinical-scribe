import { motion } from 'framer-motion';
import type { Medication } from '@/types/contracts';
import { SafetyFlagBadge } from './SafetyFlagBadge';

interface Props {
  medication: Medication;
  isFlagAcknowledged: (key: string) => boolean;
  onAcknowledgeFlag: (key: string) => void;
}

export function MedicationRow({ medication, isFlagAcknowledged, onAcknowledgeFlag }: Props) {
  const hasFlags = medication.flags.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      data-testid={`medication-${medication.id}`}
      className={`rounded-xl border p-4 transition-all ${
        hasFlags
          ? 'border-safety-flag-amber/20 bg-safety-flag-amber/[0.02]'
          : 'border-white/[0.06] bg-white/[0.02]'
      }`}
    >
      <div className="flex items-center gap-3 mb-3">
        <span className="text-lg">💊</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-white">{medication.verbatim}</h4>
            <span className="badge-ai text-[10px]">AI-drafted</span>
            {medication.needs_manual_confirmation && (
              <span className="badge-warning text-[10px]">Manual confirm needed</span>
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
      </div>

      {/* Safety flags — rendered inline next to the drug */}
      {hasFlags && (
        <div className="space-y-2 mt-2">
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
