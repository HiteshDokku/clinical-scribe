import { motion } from 'framer-motion';

interface Props {
  canSign: boolean;
  blockingReasons: string[];
  onSign: () => void;
}

/**
 * The final Sign & Submit button.
 * Disabled by default — only enabled when ALL ungrounded statements are
 * double-confirmed and ALL safety flags are individually acknowledged.
 *
 * Deliberately, there is no "Approve All" action anywhere.
 */
export function SignButton({ canSign, blockingReasons, onSign }: Props) {
  return (
    <div className="mt-8" data-testid="sign-section">
      {/* Blocking reasons */}
      {blockingReasons.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-xl bg-safety-flag-amber/[0.06] border border-safety-flag-amber/15 p-4 mb-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-4 h-4 text-safety-flag-amber" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
            </svg>
            <span className="text-xs font-semibold text-safety-flag-amber uppercase tracking-wide">
              Sign-off blocked
            </span>
          </div>
          <ul className="space-y-1">
            {blockingReasons.map((reason, i) => (
              <li key={i} className="text-xs text-gray-400 flex items-start gap-2">
                <span className="text-safety-flag-amber mt-0.5">•</span>
                {reason}
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      <motion.button
        onClick={onSign}
        disabled={!canSign}
        className="btn-primary w-full py-3 text-base"
        data-testid="sign-button"
        whileHover={canSign ? { scale: 1.01 } : {}}
        whileTap={canSign ? { scale: 0.98 } : {}}
      >
        {canSign ? (
          <>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
            </svg>
            Sign &amp; Submit
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
            </svg>
            Sign &amp; Submit
          </>
        )}
      </motion.button>

      {canSign && (
        <p className="text-xs text-gray-500 text-center mt-2">
          All items reviewed. Ready for sign-off.
        </p>
      )}
    </div>
  );
}
