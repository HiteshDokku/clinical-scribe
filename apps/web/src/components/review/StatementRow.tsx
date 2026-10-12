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
  onManualDetermination?: (id: string, text: string) => void;
  manualDetermination?: string;
  serverError?: string;
}

export function StatementRow({
  statement,
  isUngrounded,
  isReviewed,
  onReview,
  onManualDetermination,
  manualDetermination,
  evidenceMap,
  index,
  serverError,
}: Props) {
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(statement.text);
  const [typedDetermination, setTypedDetermination] = useState(manualDetermination || '');
  
  const isRequiresReview = statement.risk_tier === 'requires_review';
  const isRedFlag = statement.risk_tier === 'red_flag';
  const isHighRisk = isRequiresReview || isRedFlag;

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

  const handleManualConfirm = () => {
    if (typedDetermination.trim().length >= 3 && onManualDetermination) {
      onManualDetermination(statement.id, typedDetermination.trim());
      onReview(statement.id);
    }
  };

  const handleSaveAndConfirm = () => {
    if (editText.trim().length >= 3) {
      if (onManualDetermination) {
        onManualDetermination(statement.id, editText.trim());
      }
      onReview(statement.id);
      setIsEditing(false);
    }
  };

  if (isHighRisk) {
    return (
      <motion.div
        id={`item-${statement.id}`}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.05, duration: 0.3 }}
        data-statement-id={statement.id}
        data-source="ai"
        data-reviewed={isReviewed ? 'true' : undefined}
        className={`rounded-xl border transition-all duration-200 overflow-hidden ${
          isReviewed
            ? 'border-safety-success/20 bg-safety-success/[0.03]'
            : isRedFlag
              ? 'border-red-500/40 bg-red-900/10'
              : 'border-amber-500/40 bg-amber-900/10'
        }`}
      >
        <div className="p-4">
          {/* Header wording per Part 4 rules */}
          {isRedFlag ? (
            <p className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2">
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              High-risk presentation ({statement.reasoning_basis || 'red_flag_trigger'}): independent assessment required
            </p>
          ) : (
            <p className="text-sm font-semibold text-amber-400 mb-2 flex items-center gap-2">
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              No reviewed match: enter your own diagnosis
            </p>
          )}

          {/* Inline server error display */}
          {serverError && (
            <div className="mb-3 p-2.5 rounded-lg bg-red-950/80 border border-red-500/50 text-red-200 text-xs flex items-center gap-2" role="alert">
              <svg className="w-4 h-4 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{serverError}</span>
            </div>
          )}

          {/* The AI sentence is deliberately NOT shown anywhere on the card */}
          {isReviewed ? (
            <div>
              <div className="bg-white/5 p-3 rounded-lg text-sm text-gray-200 whitespace-pre-wrap border border-white/10">
                <span className="text-xs text-safety-success font-semibold block mb-1">Clinician Determination (Confirmed):</span>
                {manualDetermination || typedDetermination}
              </div>
              <div className="mt-2 flex justify-end">
                <button
                  onClick={() => {
                    setTypedDetermination(manualDetermination || typedDetermination);
                  }}
                  className="btn-ghost text-xs px-2.5 py-1"
                >
                  Edit
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <textarea
                value={typedDetermination}
                onChange={(e) => setTypedDetermination(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    if (typedDetermination.trim().length >= 3) {
                      handleManualConfirm();
                    }
                  }
                }}
                className={`w-full bg-clinical-900/80 border rounded-lg p-3 text-sm text-gray-200 focus:outline-none min-h-[80px] ${
                  isRedFlag ? 'border-red-500/50 focus:border-red-400' : 'border-amber-500/50 focus:border-amber-400'
                }`}
                placeholder="Enter clinical determination (required)..."
                aria-describedby={`desc-item-${statement.id}`}
              />
              <div className="flex items-center justify-between">
                <span id={`desc-item-${statement.id}`} className="text-[11px] text-gray-400">
                  Ctrl+Enter to confirm (min 3 chars)
                </span>
                <button
                  disabled={typedDetermination.trim().length < 3}
                  title={typedDetermination.trim().length < 3 ? "Enter at least 3 characters for your clinical determination" : "Confirm determination"}
                  aria-describedby={`desc-item-${statement.id}`}
                  onClick={handleManualConfirm}
                  className={`rounded-lg px-4 py-2 text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                    isRedFlag
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30'
                  }`}
                  data-testid={`confirm-btn-${statement.id}`}
                >
                  Confirm
                </button>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    );
  }

  return (
    <>
      <motion.div
        id={`item-${statement.id}`}
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
          {/* Inline server error display */}
          {serverError && (
            <div className="mb-3 p-2.5 rounded-lg bg-red-950/80 border border-red-500/50 text-red-200 text-xs flex items-center gap-2" role="alert">
              <svg className="w-4 h-4 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{serverError}</span>
            </div>
          )}

          {isEditing ? (
            <div className="flex flex-col gap-2">
              <label htmlFor={`edit-${statement.id}`} className="text-xs text-gray-400 font-medium">
                Edit statement text:
              </label>
              <textarea
                id={`edit-${statement.id}`}
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className="w-full bg-clinical-900 border border-clinical-600 rounded-lg p-2.5 text-sm text-gray-200 focus:outline-none focus:border-clinical-400 min-h-[70px]"
                aria-describedby={`edit-hint-${statement.id}`}
              />
              <div className="flex items-center justify-between">
                <span id={`edit-hint-${statement.id}`} className="text-[11px] text-gray-400">
                  Minimum 3 characters
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setIsEditing(false);
                      setEditText(statement.text);
                    }}
                    className="btn-ghost text-xs px-3 py-1.5"
                  >
                    Cancel
                  </button>
                  <button
                    disabled={editText.trim().length < 3}
                    title={editText.trim().length < 3 ? "Edited statement must contain at least 3 characters" : "Save and confirm statement"}
                    aria-describedby={`edit-hint-${statement.id}`}
                    onClick={handleSaveAndConfirm}
                    className="btn-primary text-xs px-3 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid={`save-confirm-btn-${statement.id}`}
                  >
                    Save & confirm
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3">
              {/* Click area for evidence */}
              <button
                onClick={handleClick}
                className="flex-1 text-left group"
                aria-expanded={isEvidenceOpen}
                disabled={!statement.evidence || statement.evidence.length === 0}
              >
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  {statement.statement_type === 'clinician_entered' ? (
                    <span className="text-[10px] bg-blue-900/40 text-blue-300 border border-blue-500/40 px-2 py-0.5 rounded-full font-medium" data-testid="clinician-entered-badge">
                      Clinician-entered
                    </span>
                  ) : (
                    <span className="badge-ai text-[10px]">AI-drafted</span>
                  )}
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
                      Confirmed
                    </span>
                  )}
                  {/* Fixed confidence badge: shrink-0 whitespace-nowrap, safe null check, bounds check */}
                  {statement.confidence != null && !isNaN(statement.confidence) && (
                    <span className="text-[10px] text-gray-400 ml-auto font-mono shrink-0 whitespace-nowrap">
                      {Math.round(statement.confidence <= 1 ? statement.confidence * 100 : statement.confidence)}% conf.
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-200 leading-relaxed">{editText !== statement.text ? editText : statement.text}</p>
                
                {statement.evidence && statement.evidence.length > 0 ? (
                  <p className="text-[10px] text-gray-500 mt-2 group-hover:text-clinical-400 transition-colors">
                    {isEvidenceOpen ? '▼ Hide evidence' : '▶ Click to view evidence'}
                    {' · '}
                    {statement.evidence.length} span{statement.evidence.length !== 1 ? 's' : ''}
                  </p>
                ) : statement.statement_type === 'clinician_entered' ? null : (
                  <div className="mt-2 text-xs text-clinical-300/80 bg-clinical-900/20 p-2 rounded border border-clinical-700/30">
                    <span className="font-medium text-clinical-400">AI Reasoning:</span> {statement.reasoning_basis}
                  </div>
                )}
              </button>

              {/* Single explicit action per grounded statement */}
              <div className="shrink-0 flex items-center gap-2">
                {!isReviewed ? (
                  <>
                    <button
                      onClick={() => setIsEditing(true)}
                      className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-gray-300 bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] transition-all"
                      title="Edit this statement"
                    >
                      Edit
                    </button>
                    <motion.button
                      onClick={handleReview}
                      className={`
                        rounded-lg px-3 py-1.5 text-xs font-medium transition-all
                        ${isUngrounded
                          ? 'bg-safety-ungrounded/10 text-safety-ungrounded border border-safety-ungrounded/20 hover:bg-safety-ungrounded/20'
                          : 'bg-clinical-600/30 text-clinical-300 border border-clinical-500/40 hover:bg-clinical-600/50'
                        }
                      `}
                      whileTap={{ scale: 0.95 }}
                      data-testid={`review-btn-${statement.id}`}
                      title={isUngrounded ? "Confirm ungrounded statement (requires secondary confirmation)" : "Confirm statement"}
                    >
                      Confirm
                    </motion.button>
                  </>
                ) : (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="rounded-lg px-2.5 py-1 text-xs text-gray-400 hover:text-gray-200 transition-colors"
                    title="Edit confirmed statement"
                  >
                    Edit
                  </button>
                )}
              </div>
            </div>
          )}

          {statement.evidence && statement.evidence.length > 0 && !isEditing && (
            <EvidencePanel
              evidenceIds={statement.evidence}
              evidenceMap={evidenceMap}
              isOpen={isEvidenceOpen}
            />
          )}
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
