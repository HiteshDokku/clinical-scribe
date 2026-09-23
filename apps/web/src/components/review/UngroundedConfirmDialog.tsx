import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  isOpen: boolean;
  statementText: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Two-step confirmation dialog for ungrounded statements.
 * This enforces the requirement that ungrounded statements cannot be silently approved.
 */
export function UngroundedConfirmDialog({ isOpen, statementText, onConfirm, onCancel }: Props) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="modal-overlay"
          data-testid="ungrounded-confirm-dialog"
          onClick={onCancel}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Warning icon */}
            <div className="flex justify-center mb-5">
              <div className="w-14 h-14 rounded-2xl bg-safety-ungrounded/20 flex items-center justify-center">
                <svg className="w-7 h-7 text-safety-ungrounded" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
              </div>
            </div>

            <h3 className="text-lg font-bold text-white text-center mb-2">
              Ungrounded Statement
            </h3>

            <p className="text-sm text-gray-400 text-center mb-4">
              This statement lacks full transcript grounding. The safety service could not
              verify it against the recorded evidence. Are you sure you want to approve it?
            </p>

            {/* The statement in question */}
            <div className="rounded-lg bg-safety-ungrounded/[0.08] border border-safety-ungrounded/20 p-3 mb-6">
              <p className="text-sm text-gray-200 italic">"{statementText}"</p>
            </div>

            <div className="flex gap-3">
              <motion.button
                onClick={onCancel}
                className="btn-secondary flex-1"
                whileTap={{ scale: 0.97 }}
                data-testid="ungrounded-cancel-btn"
              >
                Cancel
              </motion.button>
              <motion.button
                onClick={onConfirm}
                className="btn-danger flex-1"
                whileTap={{ scale: 0.97 }}
                data-testid="ungrounded-confirm-btn"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
                Confirm Approval
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
