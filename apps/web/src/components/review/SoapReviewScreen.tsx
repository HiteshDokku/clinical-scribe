import { useState } from 'react';
import { motion } from 'framer-motion';
import type { SoapNote, StatementList } from '@/types/contracts';
import { SectionHeader } from './SectionHeader';
import { StatementRow } from './StatementRow';
import { MedicationRow } from './MedicationRow';
import { SignButton } from './SignButton';
import { useReviewState } from '@/hooks/useReviewState';

interface Props {
  soapNote: SoapNote;
  evidenceMap: Record<string, string>;
  onSign: (editedSections: Record<string, string>) => void;
}

type SectionKey = 'subjective' | 'objective' | 'assessment' | 'plan';

const SECTION_TITLES: Record<SectionKey, string> = {
  subjective: 'Subjective',
  objective: 'Objective',
  assessment: 'Assessment',
  plan: 'Plan',
};

export function SoapReviewScreen({ soapNote, evidenceMap, onSign }: Props) {
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [draftText, setDraftText] = useState<string>('');

  const {
    reviewState,
    isStatementReviewed,
    isFlagAcknowledged,
    reviewStatement,
    acknowledgeSafetyFlag,
    approveSection,
    canSign,
    blockingReasons,
  } = useReviewState(soapNote);

  const ungroundedIds = new Set(soapNote.grounding.ungrounded_ids);

  const renderSection = (key: SectionKey, statements: StatementList) => {
    const isApproved = reviewState.sectionApprovals[key];
    const isEditing = editingSection === key;
    const customText = reviewState.sectionEdits[key];

    const handleEditClick = () => {
      setEditingSection(key);
      if (customText !== undefined) {
        setDraftText(customText);
      } else {
        setDraftText(statements.map(s => s.text).join('\n'));
      }
    };

    const handleSave = () => {
      approveSection(key, draftText);
      setEditingSection(null);
    };

    const handleApprove = () => {
      approveSection(key, customText);
    };

    const actions = (
      <>
        {!isApproved && !isEditing && (
          <>
            <button onClick={handleApprove} className="btn-primary text-xs px-3 py-1.5 min-w-[80px]">Approve</button>
            <button onClick={handleEditClick} className="btn-secondary text-xs px-3 py-1.5 min-w-[80px]">Edit</button>
          </>
        )}
        {isApproved && !isEditing && (
          <>
            <span className="text-safety-success text-xs font-bold flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
              Approved
            </span>
            <button onClick={handleEditClick} className="btn-ghost text-xs px-3 py-1.5 ml-2">Edit</button>
          </>
        )}
        {isEditing && (
          <>
            <button onClick={() => setEditingSection(null)} className="btn-ghost text-xs px-3 py-1.5">Cancel</button>
            <button onClick={handleSave} className="btn-primary text-xs px-3 py-1.5">Save & Approve</button>
          </>
        )}
      </>
    );

    return (
      <div key={key} className={`border rounded-xl p-4 transition-colors ${isApproved ? 'border-safety-success/30 bg-safety-success/5' : 'border-clinical-700/50'}`}>
        <SectionHeader
          title={SECTION_TITLES[key]}
          sectionKey={key}
          count={customText !== undefined ? undefined : statements.length}
          actions={actions}
        />
        
        {isEditing ? (
          <div className="mt-3">
            <textarea
              className="w-full bg-clinical-900 border border-clinical-700 rounded-lg p-3 text-sm text-gray-200 focus:outline-none focus:border-clinical-500 min-h-[100px]"
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
            />
          </div>
        ) : customText !== undefined ? (
          <div className="mt-3 text-sm text-gray-200 whitespace-pre-wrap pl-2 border-l-2 border-clinical-600">
            {customText}
          </div>
        ) : (
          <div className="space-y-2 mt-3">
            {statements.map((stmt, i) => (
              <StatementRow
                key={stmt.id}
                statement={stmt}
                isUngrounded={ungroundedIds.has(stmt.id)}
                isReviewed={isStatementReviewed(stmt.id)}
                onReview={reviewStatement}
                evidenceMap={evidenceMap}
                index={i}
              />
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      data-testid="soap-review-screen"
    >
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-clinical-600/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-clinical-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">SOAP Note Review</h2>
            <p className="text-xs text-gray-400">
              Encounter {soapNote.encounter_id} · Generated by {soapNote.model.name}
            </p>
          </div>
        </div>

        {/* Grounding summary */}
        <div className="flex items-center gap-4 mt-4">
          <div className="glass-card px-3 py-2 text-center">
            <p className="text-lg font-bold text-white">{soapNote.grounding.statements_total}</p>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide">Statements</p>
          </div>
          <div className={`glass-card px-3 py-2 text-center ${
            soapNote.grounding.ungrounded > 0 ? 'border-safety-ungrounded/20' : ''
          }`}>
            <p className={`text-lg font-bold ${
              soapNote.grounding.ungrounded > 0 ? 'text-safety-ungrounded' : 'text-safety-success'
            }`}>
              {soapNote.grounding.ungrounded}
            </p>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide">Ungrounded</p>
          </div>
          <div className={`glass-card px-3 py-2 text-center ${
            (soapNote.safety_flags?.length ?? 0) > 0 ? 'border-safety-flag-amber/20' : ''
          }`}>
            <p className={`text-lg font-bold ${
              (soapNote.safety_flags?.length ?? 0) > 0 ? 'text-safety-flag-amber' : 'text-safety-success'
            }`}>
              {soapNote.safety_flags?.length ?? 0}
            </p>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide">Safety Flags</p>
          </div>
        </div>
      </div>

      {/* SOAP Sections */}
      <div className="space-y-4">
        {renderSection('subjective', soapNote.sections.subjective)}
        {renderSection('objective', soapNote.sections.objective)}
        {renderSection('assessment', soapNote.sections.assessment)}
        {renderSection('plan', soapNote.sections.plan)}
      </div>

      {/* Medications */}
      {soapNote.medications && soapNote.medications.length > 0 && (() => {
        const key = 'medications';
        const isApproved = reviewState.sectionApprovals[key];
        const isEditing = editingSection === key;
        const customText = reviewState.sectionEdits[key];

        const handleEditClick = () => {
          setEditingSection(key);
          if (customText !== undefined) {
            setDraftText(customText);
          } else {
            setDraftText(soapNote.medications!.map(m => `${m.verbatim}${m.dose?.value ? ` ${m.dose.value} ${m.dose.unit || ''}` : ''}`).join('\n'));
          }
        };

        const handleSave = () => {
          approveSection(key, draftText);
          setEditingSection(null);
        };

        const handleApprove = () => {
          approveSection(key, customText);
        };

        const actions = (
          <>
            {!isApproved && !isEditing && (
              <>
                <button onClick={handleApprove} className="btn-primary text-xs px-3 py-1.5 min-w-[80px]">Approve</button>
                <button onClick={handleEditClick} className="btn-secondary text-xs px-3 py-1.5 min-w-[80px]">Edit</button>
              </>
            )}
            {isApproved && !isEditing && (
              <>
                <span className="text-safety-success text-xs font-bold flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  Approved
                </span>
                <button onClick={handleEditClick} className="btn-ghost text-xs px-3 py-1.5 ml-2">Edit</button>
              </>
            )}
            {isEditing && (
              <>
                <button onClick={() => setEditingSection(null)} className="btn-ghost text-xs px-3 py-1.5">Cancel</button>
                <button onClick={handleSave} className="btn-primary text-xs px-3 py-1.5">Save & Approve</button>
              </>
            )}
          </>
        );

        return (
          <div className={`mt-4 border rounded-xl p-4 transition-colors ${isApproved ? 'border-safety-success/30 bg-safety-success/5' : 'border-clinical-700/50'}`}>
            <SectionHeader
              title="Medications"
              sectionKey="medications"
              count={customText !== undefined ? undefined : soapNote.medications.length}
              actions={actions}
            />
            
            {isEditing ? (
              <div className="mt-3">
                <textarea
                  className="w-full bg-clinical-900 border border-clinical-700 rounded-lg p-3 text-sm text-gray-200 focus:outline-none focus:border-clinical-500 min-h-[100px]"
                  value={draftText}
                  onChange={(e) => setDraftText(e.target.value)}
                />
              </div>
            ) : customText !== undefined ? (
              <div className="mt-3 text-sm text-gray-200 whitespace-pre-wrap pl-2 border-l-2 border-clinical-600">
                {customText}
              </div>
            ) : (
              <div className="space-y-3 mt-3">
                {soapNote.medications.map((med) => (
                  <MedicationRow
                    key={med.id}
                    medication={med}
                    isFlagAcknowledged={isFlagAcknowledged}
                    onAcknowledgeFlag={acknowledgeSafetyFlag}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })()}

      {/* Sign Button */}
      <SignButton
        canSign={canSign}
        blockingReasons={blockingReasons}
        onSign={() => onSign(reviewState.sectionEdits)}
      />
    </motion.div>
  );
}
