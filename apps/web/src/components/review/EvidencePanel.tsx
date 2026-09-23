import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  evidenceIds: string[];
  evidenceMap: Record<string, string>;
  isOpen: boolean;
}

export function EvidencePanel({ evidenceIds, evidenceMap, isOpen }: Props) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="overflow-hidden"
        >
          <div className="mt-3 pl-4 border-l-2 border-clinical-600/30 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-clinical-400 mb-2">
              Supporting Evidence
            </p>
            {evidenceIds.map((id) => (
              <div
                key={id}
                className="rounded-lg bg-clinical-600/[0.06] border border-clinical-500/10 p-3"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono text-clinical-500 bg-clinical-600/20 px-1.5 py-0.5 rounded">
                    {id}
                  </span>
                </div>
                <p className="text-xs text-gray-300 leading-relaxed italic">
                  "{evidenceMap[id] ?? 'Transcript segment not available'}"
                </p>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
