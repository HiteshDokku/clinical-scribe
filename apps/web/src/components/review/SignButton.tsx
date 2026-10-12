import { motion } from 'framer-motion';
import type { BlockingItem } from '@/hooks/useReviewState';

interface Props {
  canSign: boolean;
  blockingReasons?: string[];
  blockingItems?: BlockingItem[];
  onSign: () => void;
  label?: string;
  isSubmitting?: boolean;
  onScrollToItem?: (itemId: string) => void;
  serverError?: string | null;
}

/**
 * The final Confirm Diagnosis / Sign Note button.
 * Enabled when every required statement and medication item has been confirmed.
 * Gated per ADR-0010: no auto-confirm, no bulk confirm.
 */
export function SignButton({
  canSign,
  blockingReasons = [],
  blockingItems = [],
  onSign,
  label = "Sign & Submit",
  isSubmitting = false,
  onScrollToItem,
  serverError,
}: Props) {
  // Normalize items
  const items: BlockingItem[] = blockingItems.length > 0
    ? blockingItems
    : blockingReasons.map((r, i) => ({ itemId: `reason-${i}`, reason: r }));

  const disabledReason = !canSign
    ? items.length > 0
      ? items[0]!.reason
      : "All items must be confirmed before proceeding"
    : undefined;

  return (
    <div className="mt-8" data-testid="sign-section">
      {/* Top-level server error banner */}
      {serverError && (
        <div className="mb-4 p-3 rounded-xl bg-red-950/80 border border-red-500/50 text-red-200 text-sm flex items-start gap-2" role="alert">
          <svg className="w-5 h-5 shrink-0 text-red-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <p className="font-semibold text-red-300">Action Blocked</p>
            <p className="text-xs text-red-200 mt-0.5">{serverError}</p>
          </div>
        </div>
      )}

      {/* Blocking reasons panel */}
      {items.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          id="blocked-reasons-list"
          className="rounded-xl bg-safety-flag-amber/[0.06] border border-safety-flag-amber/15 p-4 mb-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-4 h-4 text-safety-flag-amber shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
            </svg>
            <span className="text-xs font-semibold text-safety-flag-amber uppercase tracking-wide">
              Sign-off blocked ({items.length} {items.length === 1 ? 'item requires' : 'items require'} confirmation)
            </span>
          </div>
          <ul className="space-y-1.5">
            {items.map((item, i) => (
              <li key={i} className="text-xs text-gray-300 flex items-start gap-2">
                <span className="text-safety-flag-amber mt-0.5">•</span>
                {onScrollToItem ? (
                  <button
                    onClick={() => onScrollToItem(item.itemId)}
                    className="text-left text-clinical-300 hover:text-clinical-200 hover:underline cursor-pointer transition-colors"
                    title={`Click to scroll to this item`}
                  >
                    {item.reason}
                  </button>
                ) : (
                  <span>{item.reason}</span>
                )}
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      <motion.button
        onClick={onSign}
        disabled={!canSign || isSubmitting}
        title={disabledReason}
        aria-describedby={!canSign ? "blocked-reasons-list" : undefined}
        className="btn-primary w-full py-3 text-base flex justify-center items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        data-testid="sign-button"
        whileHover={canSign && !isSubmitting ? { scale: 1.01 } : {}}
        whileTap={canSign && !isSubmitting ? { scale: 0.98 } : {}}
      >
        {isSubmitting ? (
          <>
            <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Processing...
          </>
        ) : canSign ? (
          <>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
            </svg>
            {label}
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
            </svg>
            {label}
          </>
        )}
      </motion.button>

      {canSign && (
        <p className="text-xs text-safety-success text-center mt-2 flex items-center justify-center gap-1 font-medium">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
          All items confirmed. Ready to proceed.
        </p>
      )}
    </div>
  );
}
