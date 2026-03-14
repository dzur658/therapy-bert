import { motion, AnimatePresence } from "motion/react";
import { AlertTriangle, X, Trash2 } from "lucide-react";

interface DeletePatientModalProps {
  isOpen: boolean;
  patientName: string;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
}

export function DeletePatientModal({
  isOpen,
  patientName,
  onClose,
  onConfirm,
}: DeletePatientModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-50"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm px-4"
          >
            <div className="bg-card rounded-2xl border border-border/60 shadow-[0_25px_65px_rgba(0,0,0,0.12)] overflow-hidden">
              {/* Close */}
              <div className="flex justify-end px-5 pt-5">
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg hover:bg-muted transition-colors"
                >
                  <X className="w-4 h-4 text-muted-foreground" />
                </button>
              </div>

              {/* Body */}
              <div className="px-6 pb-6 pt-2 text-center">
                {/* Warning icon */}
                <div className="w-14 h-14 rounded-2xl bg-destructive/10 border border-destructive/20 flex items-center justify-center mx-auto mb-4">
                  <AlertTriangle className="w-6 h-6 text-destructive" />
                </div>

                <h2 className="text-foreground tracking-tight mb-1">
                  Delete Patient Record
                </h2>
                <p className="text-sm text-muted-foreground mb-1">
                  You are about to permanently delete
                </p>
                <p className="text-foreground mb-4">
                  <span className="text-primary">{patientName}</span>
                </p>

                {/* Warning banner */}
                <div className="bg-destructive/8 border border-destructive/20 rounded-xl px-4 py-3 mb-6 text-left">
                  <p className="text-xs text-destructive/90 leading-relaxed">
                    <span className="font-semibold">This action is permanent and cannot be undone.</span>{" "}
                    All session transcripts, knowledge graph data, nodes, edges, and associated
                    records for this patient will be irreversibly erased from this device.
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={onClose}
                    className="flex-1 px-4 py-2.5 rounded-xl border border-border/60 text-muted-foreground hover:bg-muted/50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={onConfirm}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-destructive text-white hover:bg-destructive/90 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
