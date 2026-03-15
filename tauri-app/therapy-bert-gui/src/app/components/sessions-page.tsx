import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router";
import { usePatients } from "../context/patient-context";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowLeft,
  FileText,
  ChevronDown,
  ChevronRight,
  Clock,
  MoreHorizontal,
  Trash2,
  AlertTriangle,
  Share2,
  Sparkles,
  X,
  Loader2,
  Quote,
} from "lucide-react";
import {
  TranscriptManager,
  type TranscriptLine,
  type DbSession,
} from "../services/transcript-manager";
import {
  RepresentationService,
  type AnalyzeResponse,
} from "../services/representation-service";
import {
  ContextMenu,
  ContextMenuTrigger,
  ContextMenuContent,
  ContextMenuItem,
} from "./ui/context-menu";

function formatSessionDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function sessionPreview(raw: string): string {
  try {
    const data = JSON.parse(raw);
    const lines: TranscriptLine[] = data.transcript ?? [];
    const first = lines
      .slice(0, 3)
      .map((l) => l.text)
      .join(" ");
    return first.length > 140 ? first.slice(0, 140) + "…" : first;
  } catch {
    return "Transcript available";
  }
}

function parseTranscriptLines(raw: string): TranscriptLine[] {
  try {
    const data = JSON.parse(raw);
    return (data.transcript as TranscriptLine[]) ?? [];
  } catch {
    return [];
  }
}

function speakerBadge(speaker: string): {
  label: string;
  color: string;
  bg: string;
} {
  if (speaker === "Patient")
    return { label: "Patient", color: "text-primary", bg: "bg-primary/10" };
  if (speaker === "Therapist")
    return {
      label: "Therapist",
      color: "text-violet-500",
      bg: "bg-violet-500/10",
    };
  if (speaker === "SPEAKER_09")
    return {
      label: "UNKNOWN",
      color: "text-yellow-600 dark:text-yellow-400",
      bg: "bg-yellow-500/10",
    };
  if (speaker === "SPEAKER_01")
    return {
      label: "SPEAKER_01",
      color: "text-blue-500",
      bg: "bg-blue-500/10",
    };
  if (speaker === "SPEAKER_02")
    return {
      label: "SPEAKER_02",
      color: "text-orange-500",
      bg: "bg-orange-500/10",
    };
  return { label: speaker, color: "text-muted-foreground", bg: "bg-muted/60" };
}

function SessionCard({
  session,
  index,
  onDelete,
  onReveal,
}: {
  session: DbSession;
  index: number;
  onDelete: (id: string) => void;
  onReveal: (text: string) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [hasSelection, setHasSelection] = useState(false);
  const selectionRef = useRef("");
  const menuRef = useRef<HTMLDivElement>(null);

  const captureSelection = useCallback(() => {
    const sel = window.getSelection()?.toString().trim() ?? "";
    selectionRef.current = sel;
    setHasSelection(sel.length > 0);
  }, []);
  const lines = parseTranscriptLines(session.transcript_json);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.3 }}
      className="bg-card rounded-2xl border border-border/60 overflow-hidden"
    >
      <div
        onClick={() => setExpanded((o) => !o)}
        className="px-6 py-5 hover:bg-muted/20 transition-colors cursor-pointer"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2.5 mb-1.5">
              <ChevronRight
                className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${
                  expanded ? "rotate-90" : ""
                }`}
              />
              <span className="text-sm text-foreground font-medium">
                {formatSessionDate(session.created_at)}
              </span>
              <span className="text-[11px] text-muted-foreground/60">
                &middot;
              </span>
              <div className="flex items-center gap-1 text-muted-foreground">
                <Clock className="w-3 h-3" />
                <span className="text-[11px]">{lines.length} turns</span>
              </div>
            </div>
            {!expanded && (
              <p className="text-xs text-muted-foreground leading-relaxed pl-6.5">
                {sessionPreview(session.transcript_json)}
              </p>
            )}
          </div>

          <div ref={menuRef} className="relative flex-shrink-0 mt-0.5">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen((o) => !o);
              }}
              className="p-1.5 rounded-lg hover:bg-muted/60 transition-opacity"
              aria-label="Session options"
            >
              <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
            </button>

            <AnimatePresence>
              {menuOpen && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: -4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: -4 }}
                  transition={{ duration: 0.13, ease: "easeOut" }}
                  className="absolute right-0 top-full mt-1 w-44 bg-card border border-border/60 rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.12)] overflow-hidden z-50"
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuOpen(false);
                      onDelete(session.id);
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-colors hover:bg-red-500/8"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                    <span className="text-sm text-red-500">Delete Session</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="overflow-hidden"
          >
            <ContextMenu>
              <ContextMenuTrigger
                asChild
                onContextMenu={captureSelection}
                onMouseUp={captureSelection}
              >
                <div className="mx-6 mb-5 bg-secondary/30 border border-border/40 rounded-xl overflow-hidden">
                  {lines.length > 0 ? (
                    <div className="max-h-[520px] overflow-y-auto divide-y divide-border/30">
                      {lines.map((line, i) => {
                        const badge = speakerBadge(line.speaker);
                        return (
                          <div key={i} className="px-4 py-3 flex gap-3">
                            <span
                              className={`text-[11px] tracking-wide flex-shrink-0 mt-0.5 px-2 py-0.5 rounded-md whitespace-nowrap ${badge.bg} ${badge.color}`}
                            >
                              {badge.label}
                            </span>
                            <p className="text-xs text-foreground/80 leading-relaxed select-text">
                              {line.text}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="px-4 py-6 text-center">
                      <p className="text-xs text-muted-foreground">
                        No transcript lines available
                      </p>
                    </div>
                  )}
                </div>
              </ContextMenuTrigger>
              <ContextMenuContent className="w-52 bg-card border-border/60 rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.12)]">
                <ContextMenuItem
                  disabled={!hasSelection}
                  onSelect={() => {
                    if (selectionRef.current) onReveal(selectionRef.current);
                  }}
                  className="flex items-center gap-2 rounded-lg"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  <span>Reveal ✨</span>
                </ContextMenuItem>
              </ContextMenuContent>
            </ContextMenu>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function RevealPanel({
  open,
  highlightedText,
  onClose,
}: {
  open: boolean;
  highlightedText: string;
  onClose: () => void;
}) {
  const [revealInput, setRevealInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setRevealInput("");
      setResult(null);
      setError(null);
      setLoading(false);
    }
  }, [open]);

  const handleAnalyze = async () => {
    if (!highlightedText || !revealInput.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await RepresentationService.analyze(
        highlightedText,
        revealInput.trim()
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-foreground/5 backdrop-blur-[2px] z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-card border-l border-border/60 shadow-[-25px_0_65px_rgba(0,0,0,0.08)] flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-border/40">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-amber-500" />
                </div>
                <div>
                  <h2 className="text-sm font-medium text-foreground">
                    Reveal ✨
                  </h2>
                  <p className="text-[11px] text-muted-foreground">
                    Representation Engineering
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg hover:bg-muted/60 transition-colors"
              >
                <X className="w-4 h-4 text-muted-foreground" />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {/* Explanation */}
              <div className="bg-primary/6 border border-primary/20 rounded-xl px-4 py-3">
                <p className="text-xs text-primary/80 leading-relaxed">
                  Representation engineering inspects the model's hidden states
                  to reveal subtext the patient may not be expressing directly.
                  Enter a direction below to steer the analysis.
                </p>
              </div>

              {/* Highlighted text */}
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                  <Quote className="w-3 h-3" />
                  Selected transcript
                </p>
                <div className="bg-secondary/30 border border-border/40 rounded-xl px-4 py-3">
                  <p className="text-xs text-foreground/80 leading-relaxed italic">
                    "{highlightedText}"
                  </p>
                </div>
              </div>

              {/* Reveal input */}
              <div>
                <label className="text-sm text-foreground mb-2 block">
                  The patient is currently...
                </label>
                <textarea
                  value={revealInput}
                  onChange={(e) => setRevealInput(e.target.value)}
                  placeholder="feeling"
                  rows={2}
                  className="w-full rounded-xl border border-border/60 bg-background px-4 py-3 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/40 resize-none transition-colors"
                />
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {[
                    "feeling anxious because",
                    "avoiding discussing",
                    "grieving over",
                    "minimizing the impact of",
                    "projecting onto others about",
                  ].map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => setRevealInput(example)}
                      className="text-[10px] text-muted-foreground hover:text-foreground bg-muted/40 hover:bg-muted/70 rounded-lg px-2 py-1 transition-colors"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>

              {/* Submit */}
              <button
                onClick={handleAnalyze}
                disabled={loading || !revealInput.trim()}
                className="w-full px-4 py-2.5 rounded-xl bg-primary text-white text-sm hover:bg-primary/90 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Revealing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Reveal ✨</span>
                  </>
                )}
              </button>

              {/* Error */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-destructive/8 border border-destructive/20 rounded-xl px-4 py-3"
                >
                  <p className="text-xs text-destructive/90 leading-relaxed">
                    <span className="font-semibold">Analysis failed.</span>{" "}
                    {error}
                  </p>
                </motion.div>
              )}

              {/* Results */}
              {result && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-4"
                >
                  {/* Baseline */}
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                      Baseline (literal)
                    </p>
                    <div className="bg-secondary/30 border border-border/40 rounded-xl px-4 py-3">
                      <p className="text-xs text-foreground/70 leading-relaxed">
                        {result.baseline}
                      </p>
                    </div>
                  </div>

                  {/* Insight */}
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-amber-500 mb-2 flex items-center gap-1.5">
                      <Sparkles className="w-3 h-3" />
                      Revealed insight
                    </p>
                    <div className="bg-amber-500/8 border border-amber-500/20 rounded-xl px-4 py-3">
                      <p className="text-xs text-foreground leading-relaxed">
                        {result.insight}
                      </p>
                    </div>
                  </div>

                  {/* Timing */}
                  <p className="text-[10px] text-muted-foreground/50 text-right">
                    Processed in {result.processing_time_seconds}s
                  </p>
                </motion.div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export function SessionsPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const { patients } = usePatients();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [sessions, setSessions] = useState<DbSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteSessionTarget, setDeleteSessionTarget] = useState<string | null>(
    null
  );
  const [revealOpen, setRevealOpen] = useState(false);
  const [revealText, setRevealText] = useState("");

  const handleReveal = useCallback((text: string) => {
    setRevealText(text);
    setRevealOpen(true);
  }, []);

  const patient = patients.find((p) => p.id === patientId);

  const loadSessions = useCallback(async () => {
    if (!patientId) return;
    setLoading(true);
    try {
      await TranscriptManager.init();
      const rows = await TranscriptManager.getSessionsForPatient(patientId);
      setSessions(rows);
    } catch (e) {
      console.error("Failed to load sessions from DB", e);
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const deleteSession = async (sessionId: string) => {
    try {
      await TranscriptManager.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (e) {
      console.error("Failed to delete session", e);
    }
  };

  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownOpen]);

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

                <div ref={dropdownRef} className="relative">
                  <button
                    onClick={() => setDropdownOpen((o) => !o)}
                    className="flex items-center gap-1.5 hover:bg-muted/40 rounded-lg px-2 py-1 transition-colors"
                  >
                    <span className="text-foreground text-sm">
                      {patient.name}
                    </span>
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
                              navigate(`/patient/${p.id}/sessions`);
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
                              <p className="text-sm text-foreground truncate">
                                {p.name}
                              </p>
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

            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-violet-500" />
              <span className="text-sm text-foreground font-medium">
                Session Transcripts
              </span>
            </div>
          </div>
        </div>
      </motion.nav>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats header */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="mb-6"
        >
          <h2 className="text-lg text-foreground font-medium mb-1">
            Previous Sessions
          </h2>
          <p className="text-sm text-muted-foreground">
            {loading
              ? "Loading sessions..."
              : `${sessions.length} session${sessions.length !== 1 ? "s" : ""} recorded for ${patient.name}`}
          </p>
        </motion.div>

        {/* Sessions list */}
        {loading ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-20"
          >
            <div className="w-10 h-10 border-2 border-primary/30 border-t-primary rounded-full animate-spin mb-4" />
            <p className="text-sm text-muted-foreground">
              Loading sessions...
            </p>
          </motion.div>
        ) : sessions.length > 0 ? (
          <div className="flex flex-col gap-3">
            {sessions.map((session, i) => (
              <SessionCard
                key={session.id}
                session={session}
                index={i}
                onDelete={(id) => setDeleteSessionTarget(id)}
                onReveal={handleReveal}
              />
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15 }}
            className="bg-card rounded-2xl border border-border/60 px-6 py-16 text-center"
          >
            <FileText className="w-12 h-12 text-muted-foreground/40 mx-auto mb-4" />
            <p className="text-muted-foreground font-medium">
              No sessions recorded yet
            </p>
            <p className="text-xs text-muted-foreground/60 mt-1">
              Upload a transcript to get started
            </p>
          </motion.div>
        )}
      </div>

      {/* Delete Session Confirmation Modal */}
      <AnimatePresence>
        {deleteSessionTarget !== null && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-50"
              onClick={() => setDeleteSessionTarget(null)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 10 }}
              transition={{
                duration: 0.25,
                ease: [0.25, 0.46, 0.45, 0.94],
              }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm px-4"
            >
              <div className="bg-card rounded-2xl border border-border/60 shadow-[0_25px_65px_rgba(0,0,0,0.12)] overflow-hidden">
                <div className="flex justify-end px-5 pt-5">
                  <button
                    onClick={() => setDeleteSessionTarget(null)}
                    className="p-1.5 rounded-lg hover:bg-muted transition-colors"
                  >
                    <X className="w-4 h-4 text-muted-foreground" />
                  </button>
                </div>

                <div className="px-6 pb-6 pt-2 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-destructive/10 border border-destructive/20 flex items-center justify-center mx-auto mb-4">
                    <AlertTriangle className="w-6 h-6 text-destructive" />
                  </div>

                  <h2 className="text-foreground tracking-tight mb-1">
                    Delete Session Transcript
                  </h2>
                  <p className="text-sm text-muted-foreground mb-4">
                    You are about to permanently delete this session transcript.
                  </p>

                  <div className="bg-destructive/8 border border-destructive/20 rounded-xl px-4 py-3 mb-4 text-left">
                    <p className="text-xs text-destructive/90 leading-relaxed">
                      <span className="font-semibold">
                        This action is permanent and cannot be undone.
                      </span>{" "}
                      The selected session transcript and its raw audio data
                      will be irreversibly erased from this device.
                    </p>
                  </div>

                  <div className="bg-primary/6 border border-primary/20 rounded-xl px-4 py-3 mb-6 text-left flex items-start gap-2.5">
                    <Share2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-primary/80 leading-relaxed">
                      The patient's knowledge graph will{" "}
                      <span className="font-semibold">not</span> be affected.
                      All previously extracted nodes, edges, and relationships
                      will remain intact.
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setDeleteSessionTarget(null)}
                      className="flex-1 px-4 py-2.5 rounded-xl border border-border/60 text-muted-foreground hover:bg-muted/50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        if (deleteSessionTarget) {
                          deleteSession(deleteSessionTarget);
                        }
                        setDeleteSessionTarget(null);
                      }}
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

      {/* Reveal Panel */}
      <RevealPanel
        open={revealOpen}
        highlightedText={revealText}
        onClose={() => setRevealOpen(false)}
      />
    </div>
  );
}
