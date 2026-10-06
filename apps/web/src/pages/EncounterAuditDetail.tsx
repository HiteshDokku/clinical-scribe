import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { getEncounter, getAudit, appendAddendum } from '@/api/encounters';
import type { SoapNote } from '@/types/contracts';

export function EncounterAuditDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [note, setNote] = useState<SoapNote | null>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const isAdmin = localStorage.getItem('demo_role') === 'admin';
  const [addendumModal, setAddendumModal] = useState<{sectionKey: string, sectionTitle: string} | null>(null);
  const [addendumText, setAddendumText] = useState("");
  const [addendumReason, setAddendumReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const loadData = () => {
    if (!id) return;
    Promise.all([
      getEncounter(id).catch(() => null),
      getAudit(id).catch(() => [])
    ])
      .then(([encounterData, logs]) => {
        if (!encounterData) throw new Error("Failed to load encounter");
        setNote(encounterData.note);
        setAuditLogs(logs);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-clinical-500/30 border-t-clinical-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !note) {
    return (
      <div className="min-h-screen p-8 text-center">
        <div className="bg-red-900/20 border border-red-500/30 text-red-200 p-6 rounded-xl inline-block font-sans shadow">
          {error || "Note not found"}
        </div>
        <div className="mt-4">
          <button onClick={() => navigate('/audit')} className="btn-secondary">Back</button>
        </div>
      </div>
    );
  }

  // Parse actual edits from audit logs
  const getSectionEdit = (sectionKey: string) => {
    // Look for a note_patch action that modifies this section
    const patchLog = auditLogs.find(l => l.action === 'note_patch' && l.diff?.after?.[sectionKey]);
    if (patchLog) {
      const original = patchLog.diff.before?.[sectionKey] || (note.sections as any)?.[sectionKey]?.statements?.map((s: any) => s.text).join('\n') || '';
      return {
        original,
        edited: patchLog.diff.after[sectionKey]
      };
    }
    return null;
  };

  const getAcknowledgedFlag = (flagId: string) => {
    const ackLog = auditLogs.find(l => l.action === 'safety_acknowledge' && l.diff?.flag_id === flagId);
    if (ackLog) {
      return { actor: ackLog.actor, timestamp: ackLog.created_at };
    }
    return null;
  };

  const handleAddendumSubmit = async () => {
    if (!addendumModal || !id || !addendumText.trim() || !addendumReason.trim()) return;
    setIsSubmitting(true);
    try {
      await appendAddendum(id, addendumModal.sectionKey, addendumText, addendumReason);
      setAddendumModal(null);
      setAddendumText("");
      setAddendumReason("");
      loadData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderSection = (title: string, sectionKey: 'subjective' | 'objective' | 'assessment' | 'plan', sectionData: any) => {
    if (!sectionData) {
      return (
        <div className="mb-6 glass-card-elevated overflow-hidden">
          <div className="bg-white/[0.03] border-b border-white/[0.08] px-4 py-3 font-bold text-slate-200 font-sans">
            {title}
          </div>
          <div className="p-4 text-sm text-slate-400 italic">No {title.toLowerCase()} recorded for this encounter.</div>
        </div>
      );
    }
    const edit = getSectionEdit(sectionKey);

    return (
      <div className="mb-6 glass-card-elevated overflow-hidden relative">
        <div className="bg-white/[0.03] border-b border-white/[0.08] px-4 py-3 font-bold text-slate-200 font-sans flex justify-between items-center">
          <span>{title}</span>
          {isAdmin && (
            <button 
              onClick={() => setAddendumModal({ sectionKey, sectionTitle: title })}
              className="text-xs bg-clinical-500/20 text-clinical-300 px-3 py-1 rounded hover:bg-clinical-500/30 transition-colors"
            >
              Append Correction
            </button>
          )}
        </div>
        <div className="p-4">
          {edit ? (
            <div className="space-y-4">
              <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                <span className="text-xs font-bold text-red-400 uppercase tracking-wider mb-1 block">AI Drafted</span>
                <p className="text-sm text-slate-300 line-through decoration-red-400">{edit.original}</p>
              </div>
              <div className="p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
                <span className="text-xs font-bold text-green-400 uppercase tracking-wider mb-1 block">Clinician Edited</span>
                <p className="text-sm text-slate-200">{edit.edited}</p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {sectionData.statements?.map((stmt: any, i: number) => (
                <div key={i} className="text-sm text-slate-300 font-sans p-2 border-l-2 border-white/[0.08]">
                  {stmt.text}
                </div>
              ))}
              {sectionData.insufficient_content && (
                <div className="text-sm text-amber-500 italic">
                  {sectionData.reason || 'Insufficient content'}
                </div>
              )}
            </div>
          )}
          
          {sectionKey === 'assessment' && sectionData.statements?.some((s: any) => s.risk_tier) && (
            <div className="mt-4 pt-4 border-t border-white/[0.08]">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Confirmed Diagnosis & Risk</h4>
              {(sectionData.statements || []).filter((s:any) => s.statement_type === 'inferred_diagnosis').map((stmt: any, i: number) => (
                <div key={i} className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-semibold text-slate-200">{stmt.text}</span>
                  {stmt.risk_tier && (
                    <span className={`text-[10px] uppercase px-2 py-0.5 rounded-full font-bold ${
                      stmt.risk_tier === 'red_flag' ? 'bg-red-900/40 text-red-300 border border-red-500/30' :
                      stmt.risk_tier === 'requires_review' ? 'bg-amber-900/40 text-amber-300 border border-amber-500/30' :
                      'bg-green-900/40 text-green-300 border border-green-500/30'
                    }`}>
                      {stmt.risk_tier.replace('_', ' ')}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
          {/* Render addendums for this section */}
          {(note as any).addendums?.filter((a: any) => a.section === sectionKey).map((addendum: any, i: number) => (
            <div key={`addendum-${i}`} className="mt-4 p-3 bg-amber-900/20 border border-amber-500/30 rounded-lg">
              <span className="text-[10px] font-bold text-amber-500 uppercase tracking-wider mb-2 block flex items-center gap-2">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Admin Correction
              </span>
              <p className="text-sm text-amber-100 mb-2">{addendum.corrected_text}</p>
              <p className="text-xs text-amber-400/80 italic font-mono mt-2 pt-2 border-t border-amber-500/20">
                Reason: {addendum.reason} ({new Date(addendum.created_at).toLocaleString()})
              </p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-8 max-w-3xl mx-auto text-slate-200"
    >
      {/* Background gradient */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-0 left-1/3 w-72 h-72 rounded-full bg-clinical-600/[0.05] blur-[100px]" />
        <div className="absolute bottom-1/4 right-0 w-80 h-80 rounded-full bg-clinical-800/[0.04] blur-[100px]" />
      </div>

      <div className="flex items-center justify-between mb-6">
        <button onClick={() => navigate('/audit')} className="btn-ghost text-sm font-semibold flex items-center gap-1">
          ← Back to Dashboard
        </button>
        <span className="px-3 py-1 bg-clinical-500/20 text-clinical-300 border border-clinical-500/30 rounded-full text-xs font-mono font-semibold">
          Encounter: {id}
        </span>
      </div>

      <h1 className="text-2xl font-bold font-sans mb-8">Encounter Audit Detail</h1>

      {renderSection('Subjective', 'subjective', note.sections?.subjective)}
      {renderSection('Objective', 'objective', note.sections?.objective)}
      {renderSection('Assessment', 'assessment', note.sections?.assessment)}
      {renderSection('Plan', 'plan', note.sections?.plan)}

      {note.medications && note.medications.length > 0 && (
        <div className="mb-6 glass-card-elevated overflow-hidden">
          <div className="bg-white/[0.03] border-b border-white/[0.08] px-4 py-3 font-bold text-slate-200 font-sans">
            Confirmed Medications & Safety Flags
          </div>
          <div className="p-4 space-y-4">
            {note.medications.map((med: any, idx: number) => {
              const hasFlags = med.flags && med.flags.length > 0;
              return (
                <div key={idx} className="p-3 border border-white/[0.06] rounded-lg bg-white/[0.02]">
                  <div className="font-semibold text-sm text-slate-200">
                    {med.verbatim} {med.dose?.value} {med.dose?.unit}
                  </div>
                  {hasFlags && (
                    <div className="mt-3 space-y-2">
                      {med.flags.map((flag: any, fIdx: number) => {
                        const ack = getAcknowledgedFlag(flag.source_ref);
                        return (
                          <div key={fIdx} className="p-2 border border-red-500/30 bg-red-900/20 rounded text-sm">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-bold text-red-400 text-xs uppercase">{flag.severity} RISK</span>
                              <span className="text-red-300 font-medium">{flag.message}</span>
                            </div>
                            {ack && (
                              <div className="text-[10px] text-slate-400 font-mono mt-2 flex items-center gap-1 border-t border-red-500/20 pt-2">
                                <svg className="w-3 h-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                                Acknowledged by <span className="font-bold text-slate-300">{ack.actor}</span> at {new Date(ack.timestamp).toLocaleString()}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Addendum Modal */}
      {addendumModal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-white/10 rounded-xl max-w-lg w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-100 mb-4">Append Correction: {addendumModal.sectionTitle}</h3>
            <p className="text-xs text-amber-500 mb-4">
              Note: This will not modify the original signed text. It will append a new version with an admin addendum.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Corrected Text</label>
                <textarea 
                  className="w-full bg-slate-800/50 border border-slate-700 rounded p-2 text-sm text-slate-200 min-h-[100px]"
                  value={addendumText}
                  onChange={e => setAddendumText(e.target.value)}
                  placeholder="Enter the correct findings..."
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Reason for Change</label>
                <input 
                  type="text"
                  className="w-full bg-slate-800/50 border border-slate-700 rounded p-2 text-sm text-slate-200"
                  value={addendumReason}
                  onChange={e => setAddendumReason(e.target.value)}
                  placeholder="e.g. Audit correction, typo..."
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button 
                onClick={() => setAddendumModal(null)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button 
                onClick={handleAddendumSubmit}
                disabled={isSubmitting || !addendumText.trim() || !addendumReason.trim()}
                className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded disabled:opacity-50 transition-colors"
              >
                {isSubmitting ? 'Saving...' : 'Save Correction'}
              </button>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
