import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, UserPlus, ArrowRight } from "lucide-react";

interface NewPatientModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (patient: {
    name: string;
    age: number;
    notes: string;
  }) => void;
}

export function NewPatientModal({ isOpen, onClose, onAdd }: NewPatientModalProps) {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [notes, setNotes] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim() && age) {
      onAdd({ name: name.trim(), age: parseInt(age), notes: notes.trim() });
      setName("");
      setAge("");
      setNotes("");
      onClose();
    }
  };

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
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md"
          >
            <div className="bg-card rounded-2xl border border-border/60 shadow-[0_25px_65px_rgba(0,0,0,0.08)] overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between px-6 pt-6 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
                    <UserPlus className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-foreground tracking-tight">New Patient</h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Onboard a new patient to begin transcript analysis
                    </p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-muted transition-colors"
                >
                  <X className="w-4 h-4 text-muted-foreground" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="px-6 pb-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1.5 uppercase tracking-wider">
                      Patient Name
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Enter full name"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-input-background border border-border/60 text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
                      autoFocus
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-muted-foreground mb-1.5 uppercase tracking-wider">
                      Age
                    </label>
                    <input
                      type="number"
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                      placeholder="Enter age"
                      min={1}
                      max={120}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-input-background border border-border/60 text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-muted-foreground mb-1.5 uppercase tracking-wider">
                      Initial Notes (Optional)
                    </label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Any relevant background or intake notes..."
                      rows={3}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-input-background border border-border/60 text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all resize-none"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-3 mt-6">
                  <button
                    type="button"
                    onClick={onClose}
                    className="flex-1 px-4 py-2.5 rounded-xl border border-border/60 text-muted-foreground hover:bg-muted/50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!name.trim() || !age}
                    className="flex-1 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    <span>Add Patient</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
