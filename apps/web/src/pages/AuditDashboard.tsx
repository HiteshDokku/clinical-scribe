import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { getEncounters } from '@/api/encounters';

export function AuditDashboard() {
  const navigate = useNavigate();
  const [encounters, setEncounters] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEncounters(undefined, undefined, 'signed')
      .then(data => {
        setEncounters(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const getStatusColor = (state: string) => {
    switch (state) {
      case 'signed':
        return 'bg-safety-success/20 text-safety-success border-safety-success/30';
      case 'degraded':
      case 'cancelled':
        return 'bg-safety-error/20 text-safety-error border-safety-error/30';
      default:
        return 'bg-clinical-500/20 text-clinical-300 border-clinical-500/30';
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-8 max-w-4xl mx-auto">
      {/* Background gradient */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-0 left-1/3 w-72 h-72 rounded-full bg-clinical-600/[0.05] blur-[100px]" />
        <div className="absolute bottom-1/4 right-0 w-80 h-80 rounded-full bg-clinical-800/[0.04] blur-[100px]" />
      </div>

      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold font-sans text-white">Audit Dashboard</h1>
        <button onClick={() => navigate('/')} className="btn-secondary">
          Home
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="w-12 h-12 border-4 border-clinical-500/30 border-t-clinical-500 rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="p-6 bg-red-900/20 border border-red-500/30 text-red-200 rounded-xl font-sans">
          Error: {error}
        </div>
      ) : (
        <div className="glass-card-elevated overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white/[0.03] border-b border-white/[0.08]">
                <th className="p-4 font-semibold text-slate-300 font-sans">Date/Time</th>
                <th className="p-4 font-semibold text-slate-300 font-sans">Patient Ref</th>
                <th className="p-4 font-semibold text-slate-300 font-sans">Diagnosis Summary</th>
                <th className="p-4 font-semibold text-slate-300 font-sans">Status</th>
              </tr>
            </thead>
            <tbody>
              {encounters.filter(e => e.state === 'signed').length === 0 ? (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-slate-400 font-sans">No encounters found.</td>
                </tr>
              ) : encounters.filter(e => e.state === 'signed').map((enc) => (
                <motion.tr 
                  key={enc.id}
                  whileHover={{ backgroundColor: 'rgba(255,255,255,0.03)' }}
                  onClick={() => navigate(`/audit/${enc.id}`)}
                  className="border-b border-white/[0.04] cursor-pointer transition-colors"
                >
                  <td className="p-4 font-mono text-sm text-slate-400 whitespace-nowrap">
                    {new Date(enc.created_at).toLocaleString()}
                  </td>
                  <td className="p-4 font-mono text-sm font-semibold text-clinical-300">
                    {enc.patient_ref}
                  </td>
                  <td className="p-4 text-sm text-slate-300 font-sans truncate max-w-[250px]">
                    {enc.confirmed_diagnosis_summary || <span className="italic text-slate-500">Pending</span>}
                  </td>
                  <td className="p-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getStatusColor(enc.state)}`}>
                      {enc.state.replace('_', ' ')}
                    </span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
