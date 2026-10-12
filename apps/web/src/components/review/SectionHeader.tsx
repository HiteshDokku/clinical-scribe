import { motion } from 'framer-motion';

interface Props {
  title: string;
  sectionKey: string;
  confirmedCount?: number;
  totalCount?: number;
  isInsufficient?: boolean;
}

const SECTION_ICONS: Record<string, string> = {
  subjective: '💬',
  objective: '🔬',
  assessment: '🧠',
  plan: '📋',
  medications: '💊',
};

const SECTION_DESCRIPTIONS: Record<string, string> = {
  subjective: 'Patient-reported symptoms and history',
  objective: 'Clinical observations and measurements',
  assessment: 'Clinical interpretation and diagnosis',
  plan: 'Treatment plan and follow-up',
  medications: 'Prescribed and recommended medications',
};

export function SectionHeader({ title, sectionKey, confirmedCount = 0, totalCount = 0, isInsufficient = false }: Props) {
  const isComplete = isInsufficient || (totalCount > 0 && confirmedCount === totalCount) || (totalCount === 0);

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-3 mb-3 mt-8 first:mt-0"
    >
      <span className="text-xl" role="img" aria-label={title}>
        {SECTION_ICONS[sectionKey] ?? '📄'}
      </span>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-white uppercase tracking-wide">
            {title}
          </h3>
          {isInsufficient ? (
            <span className="badge-success text-[10px] flex items-center gap-1">
              <svg className="w-3 h-3 text-safety-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Not discussed · Complete
            </span>
          ) : totalCount > 0 ? (
            <span className={`text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1 font-medium ${
              isComplete ? 'bg-safety-success/15 text-safety-success border border-safety-success/30' : 'bg-white/10 text-gray-300'
            }`}>
              {isComplete && (
                <svg className="w-3 h-3 text-safety-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
              {confirmedCount} of {totalCount} confirmed
            </span>
          ) : (
            <span className="badge-success text-[10px] flex items-center gap-1">
              <svg className="w-3 h-3 text-safety-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Complete
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-0.5">
          {SECTION_DESCRIPTIONS[sectionKey] ?? ''}
        </p>
      </div>
    </motion.div>
  );
}
