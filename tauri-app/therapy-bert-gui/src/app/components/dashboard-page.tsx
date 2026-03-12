import { useState, useMemo } from "react";
import { useNavigate } from "react-router";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { DashboardHeader } from "./dashboard-header";
import { PatientCard } from "./patient-card";
import { NewPatientModal } from "./new-patient-modal";
import { DeletePatientModal } from "./delete-patient-modal";
import { StatsBar } from "./stats-bar";
import { usePatients } from "../context/patient-context";
import { motion } from "motion/react";

export function DashboardPage() {
  const { patients, addPatient, deletePatient, movePatient, isDark, toggleDark } = usePatients();
  const [searchQuery, setSearchQuery] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const navigate = useNavigate();

  const filteredPatients = useMemo(() => {
    if (!searchQuery.trim()) return patients;
    const q = searchQuery.toLowerCase();
    return patients.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.topThemes.some((t) => t.toLowerCase().includes(q))
    );
  }, [patients, searchQuery]);

  const totalNodes = patients.reduce((sum, p) => sum + p.graphNodes, 0);
  const totalSessions = patients.reduce((sum, p) => sum + p.sessionsCompleted, 0);

  const deleteTarget = patients.find((p) => p.id === deleteTargetId) ?? null;

  const handleConfirmDelete = () => {
    if (deleteTargetId) {
      deletePatient(deleteTargetId);
      setDeleteTargetId(null);
    }
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="min-h-screen bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10">
          <DashboardHeader
            patientCount={patients.length}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onNewPatient={() => setIsModalOpen(true)}
            isDark={isDark}
            onToggleDark={toggleDark}
          />

          <StatsBar
            totalPatients={patients.length}
            totalNodes={totalNodes}
            totalSessions={totalSessions}
          />

          {/* Section Label */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex items-center justify-between mb-4"
          >
            <h2 className="text-muted-foreground text-xs uppercase tracking-wider">
              Patient Overview
            </h2>
            {searchQuery && (
              <span className="text-xs text-muted-foreground">
                {filteredPatients.length} result{filteredPatients.length !== 1 ? "s" : ""}
              </span>
            )}
          </motion.div>

          {/* Patient Grid */}
          {filteredPatients.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredPatients.map((patient, index) => (
                <PatientCard
                  key={patient.id}
                  patient={patient}
                  index={index}
                  onDelete={(id) => setDeleteTargetId(id)}
                  onMove={movePatient}
                  onClick={() => navigate(`/patient/${patient.id}`)}
                />
              ))}
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-20 text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
                <span className="text-2xl">🔍</span>
              </div>
              <p className="text-muted-foreground">No patients match your search</p>
              <button
                onClick={() => setSearchQuery("")}
                className="mt-3 text-sm text-primary hover:underline"
              >
                Clear search
              </button>
            </motion.div>
          )}

          {/* Footer */}
          <motion.footer
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-12 pt-6 border-t border-border/40 text-center"
          >
            <p className="text-[11px] text-muted-foreground/60 tracking-wide">
              All data is processed and stored locally on-device &middot; Therapy BERT v2.4
            </p>
          </motion.footer>
        </div>

        <NewPatientModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onAdd={addPatient}
        />

        <DeletePatientModal
          isOpen={deleteTarget !== null}
          patientName={deleteTarget?.name ?? ""}
          onClose={() => setDeleteTargetId(null)}
          onConfirm={handleConfirmDelete}
        />
      </div>
    </DndProvider>
  );
}
