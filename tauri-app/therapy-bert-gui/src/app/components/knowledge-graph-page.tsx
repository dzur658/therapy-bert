import { useParams, useNavigate } from "react-router";
import { usePatients } from "../context/patient-context";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Share2,
  Brain,
  ChevronDown,
} from "lucide-react";
import { KnowledgeGraph } from "./knowledge-graph";
import { getPatientGraph } from "./mock-graph-data";
import { useState, useRef, useEffect } from "react";

export function KnowledgeGraphPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const { patients } = usePatients();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const patient = patients.find((p) => p.id === patientId);
  const graphData = patientId && patient ? getPatientGraph(patient.id) : null;

  if (!patient) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Patient not found</p>
          <button
            onClick={() => navigate("/")}
            className="text-primary hover:underline text-sm"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Close patient switcher dropdown on outside click
  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownOpen]);

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation Bar */}
      <motion.nav
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="sticky top-0 z-30 bg-card/80 backdrop-blur-xl border-b border-border/60"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Left: Back + Patient Info */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate(`/patient/${patient.id}`)}
                className="p-2 rounded-xl hover:bg-muted/60 transition-colors"
                aria-label="Back to patient details"
              >
                <ArrowLeft className="w-4 h-4 text-muted-foreground" />
              </button>

              <div className="w-px h-6 bg-border/60" />

              <div className="flex items-center gap-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs tracking-wide"
                  style={{ backgroundColor: patient.accentColor }}
                >
                  {patient.initials}
                </div>

                {/* Patient name + dropdown */}
                <div ref={dropdownRef} className="relative">
                  <button
                    onClick={() => setDropdownOpen((o) => !o)}
                    className="flex items-center gap-1.5 hover:bg-muted/40 rounded-lg px-2 py-1 transition-colors"
                  >
                    <span className="text-foreground text-sm">{patient.name}</span>
                    <ChevronDown
                      className={`w-3.5 h-3.5 text-muted-foreground transition-transform duration-200 ${
                        dropdownOpen ? "rotate-180" : ""
                      }`}
                    />
                  </button>

                  {dropdownOpen && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95, y: -4 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95, y: -4 }}
                      transition={{ duration: 0.15, ease: "easeOut" }}
                      className="absolute left-0 top-full mt-1 w-64 bg-card border border-border/60 rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.1)] overflow-hidden z-50"
                    >
                      <div className="px-3 py-2 border-b border-border/40">
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wider">
                          Switch Patient
                        </p>
                      </div>
                      <div className="max-h-64 overflow-y-auto py-1">
                        {patients.map((p) => (
                          <button
                            key={p.id}
                            onClick={() => {
                              setDropdownOpen(false);
                              navigate(`/patient/${p.id}/graph`);
                            }}
                            className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                              p.id === patient.id
                                ? "bg-primary/8"
                                : "hover:bg-muted/40"
                            }`}
                          >
                            <div
                              className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-[10px] tracking-wide flex-shrink-0"
                              style={{ backgroundColor: p.accentColor }}
                            >
                              {p.initials}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm text-foreground truncate">{p.name}</p>
                              <p className="text-[11px] text-muted-foreground">
                                {p.sessionsCompleted} sessions
                              </p>
                            </div>
                          </button>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>
            </div>

            {/* Right: Title + Dark mode */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-primary" />
                <span className="text-sm text-foreground font-medium">
                  Knowledge Graph Connections
                </span>
              </div>
            </div>
          </div>
        </div>
      </motion.nav>

      {/* Main Content */}
      <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Graph Stats Row */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="grid grid-cols-3 gap-4 mb-6"
        >
          <div className="bg-card rounded-xl border border-border/40 p-4 text-center">
            <p className="text-xl text-foreground tabular-nums">{graphData?.entities.length ?? 0}</p>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Entities</p>
          </div>
          <div className="bg-card rounded-xl border border-border/40 p-4 text-center">
            <p className="text-xl text-foreground tabular-nums">{graphData?.relations.length ?? 0}</p>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Relations</p>
          </div>
          <div className="bg-card rounded-xl border border-border/40 p-4 text-center">
            <p className="text-xl text-foreground tabular-nums">{patient.topThemes.length}</p>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Themes</p>
          </div>
        </motion.div>

        {/* Full-page Knowledge Graph */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="bg-card rounded-2xl border border-border/60 overflow-hidden"
        >
          <div className="px-6 py-5 border-b border-border/40">
            <h3 className="text-foreground flex items-center gap-2">
              <Share2 className="w-4 h-4 text-amber-500" />
              Knowledge Graph
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              {patient.name}'s knowledge graph from LadybugDB (patient_{patient.id}_graph.lbug)
            </p>
          </div>

          <div className="p-4">
            {graphData && (
              <KnowledgeGraph
                data={graphData}
                accentColor={patient.accentColor}
                patientName={patient.name}
              />
            )}
          </div>
        </motion.div>

        {/* Themes */}
        {patient.topThemes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="mt-6"
          >
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-3">
              Top Themes
            </p>
            <div className="bg-card rounded-xl border border-border/40 p-4">
              <div className="flex flex-wrap gap-2">
                {patient.topThemes.map((theme) => (
                  <span
                    key={theme}
                    className="px-3 py-1.5 text-xs rounded-lg bg-muted/60 text-foreground"
                  >
                    {theme}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
