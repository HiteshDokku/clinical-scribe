import { motion } from 'framer-motion';
import type { SafetyFlag } from '@/types/contracts';

interface Props {
  flag: SafetyFlag;
  flagKey: string;
  isAcknowledged: boolean;
  onAcknowledge: (key: string) => void;
}

const SEVERITY_STYLES: Record<string, string> = {
  high: 'safety-flag-high',
  moderate: 'safety-flag-moderate',
  low: 'safety-flag-low',
};

const SEVERITY_ICONS: Record<string, string> = {
  high: '🔴',
  moderate: '🟠',
  low: '🟡',
};

export function SafetyFlagBadge({ flag, flagKey, isAcknowledged, onAcknowledge }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      data-testid={`safety-flag-${flagKey}`}
      data-acknowledged={isAcknowledged ? 'true' : 'false'}
      className={`${SEVERITY_STYLES[flag.severity] ?? 'safety-flag-low'} ${
        isAcknowledged ? 'opacity-60' : ''
      }`}
    >
      <div className="flex items-start gap-2">
        <span className="text-lg shrink-0" role="img" aria-label={`${flag.severity} severity`}>
          {SEVERITY_ICONS[flag.severity] ?? '⚠️'}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wide text-gray-200">
              {flag.type.replace(/_/g, ' ')}
            </span>
            <span className="text-[10px] font-mono text-gray-400 bg-white/[0.06] px-1.5 py-0.5 rounded">
              {flag.source_ref}
            </span>
            {flag.severity === 'high' && (
              <span className="badge-danger text-[10px]">HIGH</span>
            )}
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">{flag.message}</p>
          {flag.pair && flag.pair.length > 0 && (
            <div className="flex gap-1.5 mt-1.5">
              {flag.pair.map((drug) => (
                <span
                  key={drug}
                  className="text-[10px] font-mono bg-white/[0.06] text-gray-400 px-1.5 py-0.5 rounded"
                >
                  {drug}
                </span>
              ))}
            </div>
          )}
        </div>
        {!isAcknowledged ? (
          <motion.button
            onClick={() => onAcknowledge(flagKey)}
            className="shrink-0 rounded-lg bg-white/[0.08] border border-white/[0.12] px-3 py-1.5 text-xs font-semibold text-gray-200 hover:bg-white/[0.14] transition-all"
            whileTap={{ scale: 0.95 }}
            data-testid={`acknowledge-flag-${flagKey}`}
          >
            Acknowledge
          </motion.button>
        ) : (
          <span className="shrink-0 badge-success text-[10px]">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            Acknowledged
          </span>
        )}
      </div>
    </motion.div>
  );
}
