import { motion } from 'framer-motion';

interface Props {
  title: string;
  sectionKey: string;
  count: number;
}

const SECTION_ICONS: Record<string, string> = {
  subjective: '💬',
  objective: '🔬',
  assessment: '🧠',
  plan: '📋',
};

const SECTION_DESCRIPTIONS: Record<string, string> = {
  subjective: 'Patient-reported symptoms and history',
  objective: 'Clinical observations and measurements',
  assessment: 'Clinical interpretation and diagnosis',
  plan: 'Treatment plan and follow-up',
};

export function SectionHeader({ title, sectionKey, count }: Props) {
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
          <span className="badge-ai text-[10px]">
            {count} statement{count !== 1 ? 's' : ''}
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5">
          {SECTION_DESCRIPTIONS[sectionKey] ?? ''}
        </p>
      </div>
    </motion.div>
  );
}
