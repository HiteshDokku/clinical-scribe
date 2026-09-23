import { useState } from 'react';
import { motion } from 'framer-motion';
import type { SoapStatement } from '@/types/contracts';
import { EvidencePanel } from './EvidencePanel';
import { UngroundedConfirmDialog } from './UngroundedConfirmDialog';

interface Props {
  statement: SoapStatement;
  isUngrounded: boolean;
  isReviewed: boolean;
  onReview: (id: string) => void;
  evidenceMap: Record<string, string>;
  index: number;
}

export function StatementRow({
  statement,
  isUngrounded,
  isReviewed,
  onReview,
  evidenceMap,
  index,
}: Props) {
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  const handleClick = () => {
    setIsEvidenceOpen((prev) => !prev);
  };

  const handleReview = () => {
    if (isUngrounded && !isReviewed) {
      // Trigger double-confirmation for ungrounded statements
      setIsConfirmOpen(true);
    } else if (!isReviewed) {
      onReview(statement.id);
    }
  };

  const handleConfirmUngrounded = () => {
    onReview(statement.id);
    setIsConfirmOpen(false);
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.05, duration: 0.3 }}
        data-statement-id={statement.id}
        data-source="ai"
        data-ungrounded={isUngrounded ? 'true' : undefined}
        data-reviewed={isReviewed ? 'true' : undefined}
        className={`
          rounded-xl border transition-all duration-200 overflow-hidden
          ${isUngrounded && !isReviewed
            ? 'statement-ungrounded border-safety-ungrounded/30'
            : isReviewed
              ? 'border-safety-success/20 bg-safety-success/[0.03]'
              : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.1] hover:bg-white/[0.03]'
          }
        `}
      >
        <div className="p-4">
          <div className="flex items-start gap-3">
            {/* Click area for evidence */}
            <button
              onClick={handleClick}
              className="flex-1 text-left group"
              aria-expanded={isEvidenceOpen}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <span className="badge-ai text-[10px]">AI-drafted</span>
                {isUngrounded && !isReviewed && (
                  <span className="badge-warning text-[10px]">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                    </svg>
                    Ungrounded
                  </span>
                )}
                {isReviewed && (
                  <span className="badge-success text-[10px]">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                    Reviewed
                  </span>
                )}
                {statement.confidence !== undefined && (
                  <span className="text-[10px] text-gray-500 ml-auto font-mono">
                    {(statement.confidence * 100).toFixed(0)}% conf.
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-200 leading-relaxed">{statement.text}</p>
              <p className="text-[10px] text-gray-500 mt-2 group-hover:text-clinical-400 transition-colors">
                {isEvidenceOpen ? '▼ Hide evidence' : '▶ Click to view evidence'}
                {' · '}
                {statement.evidence.length} span{statement.evidence.length !== 1 ? 's' : ''}
              </p>
            </button>

            {/* Review action */}
            {!isReviewed && (
              <motion.button
                onClick={handleReview}
                className={`
                  shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-all
                  ${isUngrounded
                    ? 'bg-safety-ungrounded/10 text-safety-ungrounded border border-safety-ungrounded/20 hover:bg-safety-ungrounded/20'
                    : 'bg-white/[0.06] text-gray-300 border border-white/[0.08] hover:bg-white/[0.1]'
                  }
                `}
                whileTap={{ scale: 0.95 }}
                data-testid={`review-btn-${statement.id}`}
              >
                {isUngrounded ? 'Review ⚠' : 'Review ✓'}
              </motion.button>
            )}
          </div>

          <EvidencePanel
            evidenceIds={statement.evidence}
            evidenceMap={evidenceMap}
            isOpen={isEvidenceOpen}
          />
        </div>
      </motion.div>

      {/* Double-confirmation for ungrounded */}
      <UngroundedConfirmDialog
        isOpen={isConfirmOpen}
        statementText={statement.text}
        onConfirm={handleConfirmUngrounded}
        onCancel={() => setIsConfirmOpen(false)}
      />
    </>
  );
}
