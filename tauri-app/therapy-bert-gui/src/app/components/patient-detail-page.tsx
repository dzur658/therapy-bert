import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router";
import { usePatients } from "../context/patient-context";
import { motion, AnimatePresence } from "motion/react";
import {
  ArrowLeft,
  Upload,
  FileText,
  Share2,
  ChevronDown,
  Brain,
  Sun,
  Moon,
  Clock,
  Check,
  MoreHorizontal,
  Trash2,
  AlertTriangle,
  X,
  Zap,
  Coffee,
  Mic,
  Users,
  HelpCircle,
  ChevronRight,
} from "lucide-react";
import { KnowledgeGraph } from "./knowledge-graph";
import { getPatientGraph } from "./mock-graph-data";

// Mock previous sessions
const MOCK_SESSIONS: Record<string, { id: string; date: string; duration: string; summary: string }[]> = {
  "1": [
    { id: "s1", date: "Mar 9, 2026", duration: "52 min", summary: "Explored workplace anxiety triggers and developed a grounding technique toolkit." },
    { id: "s2", date: "Mar 2, 2026", duration: "48 min", summary: "Discussed self-esteem patterns linked to childhood experiences." },
    { id: "s3", date: "Feb 23, 2026", duration: "55 min", summary: "Cognitive restructuring around catastrophic thinking patterns." },
  ],
  "2": [
    { id: "s1", date: "Mar 7, 2026", duration: "50 min", summary: "Processing grief stages and developing coping mechanisms." },
    { id: "s2", date: "Feb 28, 2026", duration: "45 min", summary: "Family dynamics and boundary-setting exercises." },
  ],
  "3": [
    { id: "s1", date: "Mar 10, 2026", duration: "60 min", summary: "EMDR session targeting traumatic memory cluster." },
    { id: "s2", date: "Mar 3, 2026", duration: "55 min", summary: "Relationship patterns and attachment style exploration." },
    { id: "s3", date: "Feb 24, 2026", duration: "50 min", summary: "Resilience building through narrative therapy techniques." },
    { id: "s4", date: "Feb 17, 2026", duration: "58 min", summary: "Safety planning and grounding technique refinement." },
  ],
  "4": [
    { id: "s1", date: "Mar 5, 2026", duration: "45 min", summary: "Sleep hygiene assessment and behavioral activation planning." },
    { id: "s2", date: "Feb 26, 2026", duration: "42 min", summary: "Exploring social isolation patterns and motivational interviewing." },
  ],
  "5": [
    { id: "s1", date: "Mar 8, 2026", duration: "50 min", summary: "Career values clarification and identity exploration." },
    { id: "s2", date: "Mar 1, 2026", duration: "47 min", summary: "Mindfulness-based stress reduction introduction." },
    { id: "s3", date: "Feb 22, 2026", duration: "53 min", summary: "Identity integration work and journaling exercises." },
  ],
  "6": [
    { id: "s1", date: "Mar 6, 2026", duration: "55 min", summary: "Anger management triggers identification and DBT skills." },
    { id: "s2", date: "Feb 27, 2026", duration: "50 min", summary: "Communication styles analysis and assertiveness training." },
    { id: "s3", date: "Feb 20, 2026", duration: "52 min", summary: "Boundary-setting role play and cognitive rehearsal." },
  ],
};

// Mock diarized transcript preview (first 5 turns)
const MOCK_DIARIZED_PREVIEW = [
  { speaker: "SPEAKER_00", text: "Good morning, how have you been feeling since our last session?" },
  { speaker: "SPEAKER_01", text: "Honestly, not great. I've been having trouble sleeping again and the anxiety has been really bad." },
  { speaker: "SPEAKER_00", text: "I'm sorry to hear that. Can you tell me more about what's been keeping you up at night?" },
  { speaker: "SPEAKER_01", text: "It's mostly the anxiety about work. I keep replaying conversations in my head over and over." },
  { speaker: "SPEAKER_00", text: "That sounds like the rumination pattern we've discussed before. Have you been able to try any of the grounding techniques we practiced?" },
];

// Full mock diarized transcript — includes SPEAKER_09 (API code for unknown speakers)
const MOCK_FULL_TRANSCRIPT: { speaker: string; text: string }[] = [
  { speaker: "SPEAKER_00", text: "Good morning, how have you been feeling since our last session?" },
  { speaker: "SPEAKER_01", text: "Honestly, not great. I've been having trouble sleeping again and the anxiety has been really bad." },
  { speaker: "SPEAKER_00", text: "I'm sorry to hear that. Can you tell me more about what's been keeping you up at night?" },
  { speaker: "SPEAKER_01", text: "It's mostly the anxiety about work. I keep replaying conversations in my head over and over." },
  { speaker: "SPEAKER_00", text: "That sounds like the rumination pattern we've discussed before. Have you been able to try any of the grounding techniques we practiced?" },
  { speaker: "SPEAKER_01", text: "I tried the breathing exercise a couple of times but I couldn't really focus on it." },
  { speaker: "SPEAKER_00", text: "That's okay. It takes practice. What was going through your mind when you tried it?" },
  { speaker: "SPEAKER_01", text: "I kept thinking about all the things I should be doing instead of just sitting there." },
  { speaker: "SPEAKER_09", text: "Sorry to interrupt — there's a call on line two for you." },
  { speaker: "SPEAKER_00", text: "Thank you, I'll take it in just a moment. I apologise for the interruption." },
  { speaker: "SPEAKER_01", text: "No worries at all, take your time." },
  { speaker: "SPEAKER_00", text: "Let's continue. You mentioned work anxiety — can you give me a specific example from this week?" },
  { speaker: "SPEAKER_01", text: "Yes, last Tuesday my manager called a surprise meeting and I completely froze. I couldn't even speak." },
  { speaker: "SPEAKER_00", text: "What were you feeling in your body at that moment?" },
  { speaker: "SPEAKER_01", text: "My heart was racing, my palms were sweaty. I just wanted to disappear from the room." },
  { speaker: "SPEAKER_00", text: "Those are classic fight-or-flight responses. Let's work on recognising those cues earlier." },
  { speaker: "SPEAKER_01", text: "Is that something that gets easier over time?" },
  { speaker: "SPEAKER_00", text: "Absolutely — with consistent practice your window of tolerance expands." },
  { speaker: "SPEAKER_09", text: "Should I close the door for you both?" },
  { speaker: "SPEAKER_01", text: "Oh, yes please. Thank you." },
  { speaker: "SPEAKER_00", text: "Thank you. Now — when you notice those early physical signals, that is your window to engage the grounding technique before the anxiety escalates." },
  { speaker: "SPEAKER_01", text: "Okay. So I should be watching for the racing heart and then act immediately?" },
  { speaker: "SPEAKER_00", text: "Exactly. Think of it as catching the wave before it crashes rather than trying to swim out of it." },
  { speaker: "SPEAKER_01", text: "That actually makes a lot of sense the way you put it." },
];

type PipelineStep =
  | "idle"
  | "file-ready"
  | "diarize-confirm"
  | "diarizing"
  | "speaker-mapping"
  | "unknown-clarification"
  | "bert-confirm"
  | "bert-processing"
  | "complete";

// Per-session row with its own 3-dot menu
function SessionRow({
  session,
  index,
  onDelete,
}: {
  session: { id: string; date: string; duration: string; summary: string };
  index: number;
  onDelete: (id: string) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.05 }}
      className="px-6 py-4 hover:bg-muted/20 transition-colors group cursor-pointer"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-sm text-foreground">{session.date}</span>
            <span className="text-[11px] text-muted-foreground/60">&middot;</span>
            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock className="w-3 h-3" />
              <span className="text-[11px]">{session.duration}</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {session.summary}
          </p>
        </div>

        {/* 3-dot menu */}
        <div
          ref={menuRef}
          className="relative flex-shrink-0 mt-0.5"
        >
          <button
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen((o) => !o);
            }}
            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-lg hover:bg-muted/60 focus:opacity-100"
            aria-label="Session options"
          >
            <MoreHorizontal className="w-3.5 h-3.5 text-muted-foreground" />
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
                  className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-colors hover:bg-red-500/8 group/del"
                >
                  <Trash2 className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                  <span className="text-sm text-red-500">Delete Session</span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

export function PatientDetailPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const { patients, isDark, toggleDark } = usePatients();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeView, setActiveView] = useState<"upload" | "sessions" | "graph" | null>(null);
  const [uploadDragOver, setUploadDragOver] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [localSessions, setLocalSessions] = useState<
    Record<string, { id: string; date: string; duration: string; summary: string }[]>
  >({ ...MOCK_SESSIONS });
  const dropdownRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Pipeline state
  const [pipelineStep, setPipelineStep] = useState<PipelineStep>("idle");
  const [diarizeElapsed, setDiarizeElapsed] = useState(0);
  const [bertElapsed, setBertElapsed] = useState(0);
  const diarizeTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const bertTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Speaker mapping: which speaker is the patient
  const [patientSpeaker, setPatientSpeaker] = useState<"SPEAKER_00" | "SPEAKER_01" | null>(null);

  // Unknown speaker clarification
  const [unknownQueue, setUnknownQueue] = useState<number[]>([]); // indices of SPEAKER_09 in full transcript
  const [currentUnknownPos, setCurrentUnknownPos] = useState(0);
  const [selectedUnknownRole, setSelectedUnknownRole] = useState<"patient" | "practitioner" | "neither" | null>(null);

  // Delete session confirmation states
  const [deleteSessionTarget, setDeleteSessionTarget] = useState<string | null>(null);

  const patient = patients.find((p) => p.id === patientId);
  const sessions = patientId ? (localSessions[patientId] ?? []) : [];

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

  // Cleanup timers
  useEffect(() => {
    return () => {
      if (diarizeTimerRef.current) clearInterval(diarizeTimerRef.current);
      if (bertTimerRef.current) clearInterval(bertTimerRef.current);
    };
  }, []);

  const deleteSession = (sessionId: string) => {
    if (!patientId) return;
    setLocalSessions((prev) => ({
      ...prev,
      [patientId]: (prev[patientId] ?? []).filter((s) => s.id !== sessionId),
    }));
  };

  const handleFileSelect = (file: File | null) => {
    if (!file) return;
    setUploadError(null);
    if (!file.name.toLowerCase().endsWith(".wav")) {
      setUploadError("Only .wav audio files are accepted.");
      return;
    }
    setUploadedFile(file.name);
    setPipelineStep("file-ready");
  };

  const resetPipeline = () => {
    setPipelineStep("idle");
    setUploadedFile(null);
    setUploadError(null);
    setDiarizeElapsed(0);
    setBertElapsed(0);
    setPatientSpeaker(null);
    setUnknownQueue([]);
    setCurrentUnknownPos(0);
    setSelectedUnknownRole(null);
    if (diarizeTimerRef.current) clearInterval(diarizeTimerRef.current);
    if (bertTimerRef.current) clearInterval(bertTimerRef.current);
  };

  // Called when therapist confirms speaker mapping — checks for SPEAKER_09 unknowns
  const proceedFromSpeakerMapping = () => {
    const indices = MOCK_FULL_TRANSCRIPT
      .map((t, i) => (t.speaker === "SPEAKER_09" ? i : -1))
      .filter((i) => i !== -1);
    if (indices.length > 0) {
      setUnknownQueue(indices);
      setCurrentUnknownPos(0);
      setSelectedUnknownRole(null);
      setPipelineStep("unknown-clarification");
    } else {
      setPipelineStep("bert-confirm");
    }
  };

  // Move to next unknown or proceed to BERT confirmation
  const confirmUnknownAndAdvance = () => {
    const nextPos = currentUnknownPos + 1;
    if (nextPos < unknownQueue.length) {
      setCurrentUnknownPos(nextPos);
      setSelectedUnknownRole(null);
    } else {
      setPipelineStep("bert-confirm");
    }
  };

  const startDiarization = () => {
    setPipelineStep("diarizing");
    setDiarizeElapsed(0);
    diarizeTimerRef.current = setInterval(() => {
      setDiarizeElapsed((prev) => prev + 1);
    }, 1000);
    // Mock: complete after ~10 seconds
    setTimeout(() => {
      if (diarizeTimerRef.current) clearInterval(diarizeTimerRef.current);
      setPipelineStep("speaker-mapping");
      setPatientSpeaker(null);
    }, 10000);
  };

  const startBertProcessing = () => {
    setPipelineStep("bert-processing");
    setBertElapsed(0);
    bertTimerRef.current = setInterval(() => {
      setBertElapsed((prev) => prev + 1);
    }, 1000);
    // Mock: complete after ~12 seconds
    setTimeout(() => {
      if (bertTimerRef.current) clearInterval(bertTimerRef.current);
      setPipelineStep("complete");
    }, 12000);
  };

  const formatElapsed = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

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
            {/* Left: Back + Patient Info */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate("/")}
                className="p-2 rounded-xl hover:bg-muted/60 transition-colors"
                aria-label="Back to dashboard"
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

                  <AnimatePresence>
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
                                setActiveView(null);
                                resetPipeline();
                                navigate(`/patient/${p.id}`);
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
                              {p.id === patient.id && (
                                <Check className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                              )}
                            </button>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>

            {/* Right: Dark mode + meta */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground hidden sm:inline">
                Age {patient.age} &middot; {patient.sessionsCompleted} sessions
              </span>

              <button
                onClick={toggleDark}
                aria-label="Toggle dark mode"
                className="relative w-[52px] h-[28px] rounded-full border border-border/60 bg-card transition-colors duration-300 flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-primary/30"
              >
                <span
                  className="absolute inset-0 rounded-full transition-colors duration-300"
                  style={{ backgroundColor: isDark ? "rgba(14,165,160,0.2)" : "transparent" }}
                />
                <Sun
                  className="absolute left-[6px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-amber-400 transition-opacity duration-200"
                  style={{ opacity: isDark ? 0.3 : 1 }}
                />
                <Moon
                  className="absolute right-[6px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-primary transition-opacity duration-200"
                  style={{ opacity: isDark ? 1 : 0.3 }}
                />
                <motion.span
                  animate={{ x: isDark ? 24 : 2 }}
                  transition={{ type: "spring", stiffness: 500, damping: 35 }}
                  className="absolute top-[3px] w-[22px] h-[22px] rounded-full bg-primary shadow-sm"
                  style={{ left: 0 }}
                />
              </button>
            </div>
          </div>
        </div>
      </motion.nav>

      {/* Main Content */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Action Cards */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <h2 className="text-muted-foreground text-xs uppercase tracking-wider mb-4">
            Actions
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            {/* Upload Transcript */}
            <button
              onClick={() => {
                setActiveView(activeView === "upload" ? null : "upload");
                if (activeView !== "upload") resetPipeline();
              }}
              className={`group relative bg-card rounded-2xl border p-6 text-left transition-all duration-200 ${
                activeView === "upload"
                  ? "border-primary/40 shadow-[0_0_0_2px_rgba(14,165,160,0.12)]"
                  : "border-border/60 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] hover:border-primary/20"
              }`}
            >
              <div
                className="absolute top-0 left-6 right-6 h-[2px] rounded-b-full transition-opacity duration-300"
                style={{
                  backgroundColor: patient.accentColor,
                  opacity: activeView === "upload" ? 1 : 0.4,
                }}
              />
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                <Upload className="w-5 h-5 text-primary" />
              </div>
              <h3 className="text-foreground mb-1">Upload Transcript</h3>
              <p className="text-xs text-muted-foreground">
                Upload a session recording to diarize and process with BERT.
              </p>
            </button>

            {/* Inspect Previous Sessions */}
            <button
              onClick={() => setActiveView(activeView === "sessions" ? null : "sessions")}
              className={`group relative bg-card rounded-2xl border p-6 text-left transition-all duration-200 ${
                activeView === "sessions"
                  ? "border-primary/40 shadow-[0_0_0_2px_rgba(14,165,160,0.12)]"
                  : "border-border/60 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] hover:border-primary/20"
              }`}
            >
              <div
                className="absolute top-0 left-6 right-6 h-[2px] rounded-b-full transition-opacity duration-300"
                style={{
                  backgroundColor: patient.accentColor,
                  opacity: activeView === "sessions" ? 1 : 0.4,
                }}
              />
              <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center mb-4">
                <FileText className="w-5 h-5 text-violet-500" />
              </div>
              <h3 className="text-foreground mb-1">Inspect Sessions</h3>
              <p className="text-xs text-muted-foreground">
                Review previous session transcripts and their extracted themes and entities.
              </p>
            </button>

            {/* View Patient Graph */}
            <button
              onClick={() => setActiveView(activeView === "graph" ? null : "graph")}
              className={`group relative bg-card rounded-2xl border p-6 text-left transition-all duration-200 ${
                activeView === "graph"
                  ? "border-primary/40 shadow-[0_0_0_2px_rgba(14,165,160,0.12)]"
                  : "border-border/60 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] hover:border-primary/20"
              }`}
            >
              <div
                className="absolute top-0 left-6 right-6 h-[2px] rounded-b-full transition-opacity duration-300"
                style={{
                  backgroundColor: patient.accentColor,
                  opacity: activeView === "graph" ? 1 : 0.4,
                }}
              />
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center mb-4">
                <Share2 className="w-5 h-5 text-amber-500" />
              </div>
              <h3 className="text-foreground mb-1">View Patient Graph</h3>
              <p className="text-xs text-muted-foreground">
                Explore the full knowledge graph with {getPatientGraph(patient.id).entities.length} entities and {getPatientGraph(patient.id).relations.length} relations.
              </p>
            </button>
          </div>
        </motion.div>

        {/* Expanded View */}
        <AnimatePresence mode="wait">
          {activeView === "upload" && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="bg-card rounded-2xl border border-border/60 overflow-hidden"
            >
              <div className="px-6 py-5 border-b border-border/40">
                <h3 className="text-foreground flex items-center gap-2">
                  <Upload className="w-4 h-4 text-primary" />
                  Upload Session Recording
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Accepts <span className="text-primary">.wav</span> audio files only
                </p>
              </div>

              <div className="p-6">
                {/* Hidden file input */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".wav,audio/wav,audio/x-wav"
                  className="hidden"
                  onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
                />

                {/* Step: No file uploaded yet */}
                {pipelineStep === "idle" && (
                  <div
                    onDragOver={(e) => { e.preventDefault(); setUploadDragOver(true); setUploadError(null); }}
                    onDragLeave={() => setUploadDragOver(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setUploadDragOver(false);
                      handleFileSelect(e.dataTransfer.files?.[0] ?? null);
                    }}
                    className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors duration-200 ${
                      uploadDragOver
                        ? "border-primary bg-primary/5"
                        : uploadError
                        ? "border-red-400/60 bg-red-500/5"
                        : "border-border/60 hover:border-primary/30"
                    }`}
                  >
                    <div className="w-14 h-14 rounded-2xl bg-muted/50 flex items-center justify-center mx-auto mb-4">
                      <Upload className="w-6 h-6 text-muted-foreground" />
                    </div>
                    <p className="text-muted-foreground text-sm mb-1">
                      Drop your <span className="text-primary">.wav</span> file here
                    </p>
                    {uploadError ? (
                      <p className="text-xs text-red-500 mb-4">{uploadError}</p>
                    ) : (
                      <p className="text-muted-foreground/60 text-xs mb-4">or</p>
                    )}
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm"
                    >
                      Browse Files
                    </button>
                  </div>
                )}

                {/* Step: File uploaded, show Create Transcript button */}
                {pipelineStep === "file-ready" && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.98 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center py-8"
                  >
                    <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-4">
                      <Check className="w-6 h-6 text-primary" />
                    </div>
                    <p className="text-foreground mb-1">File uploaded successfully</p>
                    <p className="text-xs text-muted-foreground mb-4">{uploadedFile}</p>
                    <div className="flex items-center justify-center gap-3">
                      <button
                        onClick={() => resetPipeline()}
                        className="px-4 py-2 rounded-xl border border-border/60 text-muted-foreground hover:bg-muted/50 transition-colors text-sm"
                      >
                        Upload Another
                      </button>
                      <button
                        onClick={() => setPipelineStep("diarize-confirm")}
                        className="px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm flex items-center gap-2"
                      >
                        <Mic className="w-3.5 h-3.5" />
                        Create Transcript
                      </button>
                    </div>
                  </motion.div>
                )}

                {/* Step: Speaker mapping — diarization complete */}
                {pipelineStep === "speaker-mapping" && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35 }}
                  >
                    {/* Success banner */}
                    <div className="flex items-center gap-2.5 bg-green-500/8 border border-green-500/20 rounded-xl px-4 py-3 mb-6">
                      <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                      <div>
                        <p className="text-sm text-foreground">Transcript created successfully</p>
                        <p className="text-[11px] text-muted-foreground">
                          Diarization completed in {Math.floor(diarizeElapsed / 60)}m {diarizeElapsed % 60}s
                        </p>
                      </div>
                    </div>

                    {/* Speaker mapping instructions */}
                    <div className="mb-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Users className="w-4 h-4 text-primary" />
                        <h4 className="text-foreground text-sm">Identify Speakers</h4>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        The diarization model detected two primary speakers. Review the first few turns below
                        and select which speaker is the <span className="text-primary">patient</span> and
                        which is the <span className="text-violet-500">practitioner</span>.
                        Any unidentified lines (<span className="text-yellow-600 dark:text-yellow-400">UNKNOWN</span>) will be resolved in the next step.
                      </p>
                    </div>

                    {/* Transcript preview */}
                    <div className="bg-secondary/30 border border-border/40 rounded-xl overflow-hidden mb-5">
                      {MOCK_DIARIZED_PREVIEW.map((turn, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -6 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.08 }}
                          className={`px-4 py-3 flex gap-3 ${
                            i < MOCK_DIARIZED_PREVIEW.length - 1 ? "border-b border-border/30" : ""
                          }`}
                        >
                          <span
                            className={`text-[11px] tracking-wide flex-shrink-0 mt-0.5 px-2 py-0.5 rounded-md ${
                              turn.speaker === "SPEAKER_00"
                                ? "bg-blue-500/10 text-blue-500"
                                : "bg-orange-500/10 text-orange-500"
                            }`}
                          >
                            {turn.speaker}
                          </span>
                          <p className="text-xs text-foreground/80 leading-relaxed">
                            {turn.text}
                          </p>
                        </motion.div>
                      ))}
                    </div>

                    {/* Speaker assignment */}
                    <div className="bg-muted/30 border border-border/40 rounded-xl p-4 mb-5">
                      <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-3">
                        Who is the patient?
                      </p>
                      <div className="flex gap-3">
                        <button
                          onClick={() => setPatientSpeaker("SPEAKER_00")}
                          className={`flex-1 px-4 py-3 rounded-xl border-2 transition-all duration-200 text-left ${
                            patientSpeaker === "SPEAKER_00"
                              ? "border-primary bg-primary/8 shadow-[0_0_0_2px_rgba(14,165,160,0.12)]"
                              : "border-border/60 hover:border-primary/30"
                          }`}
                        >
                          <span className="text-[11px] tracking-wide px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-500">
                            SPEAKER_00
                          </span>
                          <p className="text-xs text-muted-foreground mt-2">
                            {patientSpeaker === "SPEAKER_00" ? (
                              <span className="text-primary">= Patient</span>
                            ) : patientSpeaker === "SPEAKER_01" ? (
                              <span className="text-violet-500">= Practitioner</span>
                            ) : (
                              "Select role"
                            )}
                          </p>
                        </button>
                        <button
                          onClick={() => setPatientSpeaker("SPEAKER_01")}
                          className={`flex-1 px-4 py-3 rounded-xl border-2 transition-all duration-200 text-left ${
                            patientSpeaker === "SPEAKER_01"
                              ? "border-primary bg-primary/8 shadow-[0_0_0_2px_rgba(14,165,160,0.12)]"
                              : "border-border/60 hover:border-primary/30"
                          }`}
                        >
                          <span className="text-[11px] tracking-wide px-2 py-0.5 rounded-md bg-orange-500/10 text-orange-500">
                            SPEAKER_01
                          </span>
                          <p className="text-xs text-muted-foreground mt-2">
                            {patientSpeaker === "SPEAKER_01" ? (
                              <span className="text-primary">= Patient</span>
                            ) : patientSpeaker === "SPEAKER_00" ? (
                              <span className="text-violet-500">= Practitioner</span>
                            ) : (
                              "Select role"
                            )}
                          </p>
                        </button>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-3">
                      <button
                        onClick={() => resetPipeline()}
                        className="px-4 py-2 rounded-xl border border-border/60 text-muted-foreground hover:bg-muted/50 transition-colors text-sm"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={proceedFromSpeakerMapping}
                        disabled={!patientSpeaker}
                        className={`px-4 py-2 rounded-xl text-sm flex items-center gap-2 transition-all ${
                          patientSpeaker
                            ? "bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.98]"
                            : "bg-muted text-muted-foreground cursor-not-allowed"
                        }`}
                      >
                        <Users className="w-3.5 h-3.5" />
                        Clarify Speakers
                      </button>
                    </div>
                  </motion.div>
                )}

                {/* ── Unknown Speaker Clarification step ── */}
                {pipelineStep === "unknown-clarification" && (() => {
                  const unknownIdx = unknownQueue[currentUnknownPos];
                  const contextStart = Math.max(0, unknownIdx - 5);
                  const contextEnd = Math.min(MOCK_FULL_TRANSCRIPT.length - 1, unknownIdx + 5);
                  const contextLines = MOCK_FULL_TRANSCRIPT.slice(contextStart, contextEnd + 1);

                  const getSpeakerLabel = (spk: string, lineIdx: number): { label: string; color: string; bg: string } => {
                    const absIdx = contextStart + lineIdx;
                    if (spk === "SPEAKER_09") {
                      if (absIdx === unknownIdx) {
                        return { label: "UNKNOWN ?", color: "text-yellow-600 dark:text-yellow-400", bg: "bg-yellow-500/10" };
                      }
                      return { label: "UNKNOWN", color: "text-muted-foreground", bg: "bg-muted/60" };
                    }
                    if (!patientSpeaker) {
                      return spk === "SPEAKER_00"
                        ? { label: "SPEAKER_00", color: "text-blue-500", bg: "bg-blue-500/10" }
                        : { label: "SPEAKER_01", color: "text-orange-500", bg: "bg-orange-500/10" };
                    }
                    const isPatient = spk === patientSpeaker;
                    return isPatient
                      ? { label: "Patient", color: "text-primary", bg: "bg-primary/10" }
                      : { label: "Practitioner", color: "text-violet-500", bg: "bg-violet-500/10" };
                  };

                  return (
                    <motion.div
                      key={`unknown-${currentUnknownPos}`}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35 }}
                    >
                      {/* Header */}
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <HelpCircle className="w-4 h-4 text-yellow-500" />
                          <h4 className="text-foreground text-sm">Clarify Unknown Speaker</h4>
                        </div>
                        <span className="text-[11px] text-muted-foreground bg-muted/50 rounded-lg px-2 py-1">
                          {currentUnknownPos + 1} of {unknownQueue.length}
                        </span>
                      </div>

                      <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                        The diarization model could not identify the speaker on the highlighted line. Review the surrounding context and assign a role.
                        Any other unidentified lines in the context window are shown as{" "}
                        <span className="text-muted-foreground bg-muted/70 rounded px-1 py-0.5">UNKNOWN</span>{" "}
                        and will be addressed separately.
                      </p>

                      {/* Context transcript window */}
                      <div className="bg-secondary/30 border border-border/40 rounded-xl overflow-hidden mb-5">
                        {contextLines.map((turn, i) => {
                          const absIdx = contextStart + i;
                          const isTarget = absIdx === unknownIdx;
                          const info = getSpeakerLabel(turn.speaker, i);
                          return (
                            <motion.div
                              key={absIdx}
                              initial={{ opacity: 0, x: -6 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: i * 0.05 }}
                              className={`px-4 py-3 flex gap-3 ${
                                i < contextLines.length - 1 ? "border-b border-border/30" : ""
                              } ${
                                isTarget
                                  ? "bg-yellow-500/6 border-l-2 border-l-yellow-500/60"
                                  : ""
                              }`}
                            >
                              <span
                                className={`text-[11px] tracking-wide flex-shrink-0 mt-0.5 px-2 py-0.5 rounded-md ${info.bg} ${info.color}`}
                              >
                                {info.label}
                              </span>
                              <p className={`text-xs leading-relaxed ${isTarget ? "text-foreground" : "text-foreground/70"}`}>
                                {turn.text}
                              </p>
                            </motion.div>
                          );
                        })}
                      </div>

                      {/* Assignment buttons */}
                      <div className="bg-muted/30 border border-border/40 rounded-xl p-4 mb-5">
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-3">
                          Who said the highlighted line?
                        </p>
                        <div className="flex gap-3">
                          <button
                            onClick={() => setSelectedUnknownRole("patient")}
                            className={`flex-1 px-4 py-3 rounded-xl border-2 transition-all duration-200 text-left ${
                              selectedUnknownRole === "patient"
                                ? "border-primary bg-primary/8 shadow-[0_0_0_2px_rgba(14,165,160,0.12)]"
                                : "border-border/60 hover:border-primary/30"
                            }`}
                          >
                            <span className="text-[11px] tracking-wide px-2 py-0.5 rounded-md bg-primary/10 text-primary">
                              Patient
                            </span>
                            <p className="text-xs text-muted-foreground mt-2">
                              {patientSpeaker ? (
                                <span className="text-muted-foreground/80">{patientSpeaker}</span>
                              ) : (
                                "The patient"
                              )}
                            </p>
                          </button>
                          <button
                            onClick={() => setSelectedUnknownRole("practitioner")}
                            className={`flex-1 px-4 py-3 rounded-xl border-2 transition-all duration-200 text-left ${
                              selectedUnknownRole === "practitioner"
                                ? "border-violet-500 bg-violet-500/8 shadow-[0_0_0_2px_rgba(139,92,246,0.12)]"
                                : "border-border/60 hover:border-violet-500/30"
                            }`}
                          >
                            <span className="text-[11px] tracking-wide px-2 py-0.5 rounded-md bg-violet-500/10 text-violet-500">
                              Practitioner
                            </span>
                            <p className="text-xs text-muted-foreground mt-2">
                              {patientSpeaker ? (
                                <span className="text-muted-foreground/80">
                                  {patientSpeaker === "SPEAKER_00" ? "SPEAKER_01" : "SPEAKER_00"}
                                </span>
                              ) : (
                                "The therapist"
                              )}
                            </p>
                          </button>
                          <button
                            onClick={() => setSelectedUnknownRole("neither")}
                            className={`flex-1 px-4 py-3 rounded-xl border-2 transition-all duration-200 text-left ${
                              selectedUnknownRole === "neither"
                                ? "border-red-400 bg-red-500/8 shadow-[0_0_0_2px_rgba(239,68,68,0.10)]"
                                : "border-border/60 hover:border-red-400/30"
                            }`}
                          >
                            <span className="text-[11px] tracking-wide px-2 py-0.5 rounded-md bg-red-500/10 text-red-500">
                              Neither
                            </span>
                            <p className="text-xs text-muted-foreground mt-2">
                              Drop this line
                            </p>
                          </button>
                        </div>
                        {selectedUnknownRole === "neither" && (
                          <motion.p
                            initial={{ opacity: 0, y: -4 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.2 }}
                            className="text-[11px] text-red-500/80 mt-3 leading-relaxed"
                          >
                            This line will be excluded from the transcript and will not influence BERT processing or the knowledge graph.
                          </motion.p>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center justify-between gap-3">
                        <button
                          onClick={() => resetPipeline()}
                          className="px-4 py-2 rounded-xl border border-border/60 text-muted-foreground hover:bg-muted/50 transition-colors text-sm"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={confirmUnknownAndAdvance}
                          disabled={!selectedUnknownRole}
                          className={`px-4 py-2 rounded-xl text-sm flex items-center gap-2 transition-all ${
                            selectedUnknownRole
                              ? "bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.98]"
                              : "bg-muted text-muted-foreground cursor-not-allowed"
                          }`}
                        >
                          {currentUnknownPos + 1 < unknownQueue.length ? (
                            <>
                              <ChevronRight className="w-3.5 h-3.5" />
                              Next Unknown
                            </>
                          ) : (
                            <>
                              <Brain className="w-3.5 h-3.5" />
                              Process with BERT
                            </>
                          )}
                        </button>
                      </div>
                    </motion.div>
                  );
                })()}
              </div>
            </motion.div>
          )}

          {activeView === "sessions" && (
            <motion.div
              key="sessions"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="bg-card rounded-2xl border border-border/60 overflow-hidden"
            >
              <div className="px-6 py-5 border-b border-border/40 flex items-center justify-between">
                <div>
                  <h3 className="text-foreground flex items-center gap-2">
                    <FileText className="w-4 h-4 text-violet-500" />
                    Previous Sessions
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    {sessions.length} session{sessions.length !== 1 ? "s" : ""} recorded
                  </p>
                </div>
              </div>

              <div className="divide-y divide-border/40">
                {sessions.length > 0 ? (
                  sessions.map((session, i) => (
                    <SessionRow
                      key={session.id}
                      session={session}
                      index={i}
                      onDelete={(id) => setDeleteSessionTarget(id)}
                    />
                  ))
                ) : (
                  <div className="px-6 py-12 text-center">
                    <p className="text-muted-foreground text-sm">No sessions recorded yet</p>
                    <p className="text-muted-foreground/60 text-xs mt-1">
                      Upload a transcript to get started
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {activeView === "graph" && (
            <motion.div
              key="graph"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
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

              <div className="p-6">
                {/* Graph Stats Row */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="bg-secondary/50 rounded-xl p-4 text-center">
                    <p className="text-xl text-foreground tabular-nums">{getPatientGraph(patient.id).entities.length}</p>
                    <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Entities</p>
                  </div>
                  <div className="bg-secondary/50 rounded-xl p-4 text-center">
                    <p className="text-xl text-foreground tabular-nums">{getPatientGraph(patient.id).relations.length}</p>
                    <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Relations</p>
                  </div>
                  <div className="bg-secondary/50 rounded-xl p-4 text-center">
                    <p className="text-xl text-foreground tabular-nums">{patient.topThemes.length}</p>
                    <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Themes</p>
                  </div>
                </div>

                {/* Explore Knowledge Graph Connections Button */}
                <button
                  onClick={() => navigate(`/patient/${patient.id}/graph`)}
                  className="w-full mb-6 px-6 py-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.98] transition-all flex items-center justify-center gap-3"
                >
                  <Brain className="w-5 h-5" />
                  <span className="text-sm font-medium">Explore Knowledge Graph Connections</span>
                  <ChevronRight className="w-4 h-4" />
                </button>

                {/* Knowledge Graph Visualization - Compact Preview */}
                <KnowledgeGraph
                  data={getPatientGraph(patient.id)}
                  accentColor={patient.accentColor}
                  patientName={patient.name}
                />

                {/* Themes */}
                {patient.topThemes.length > 0 && (
                  <div className="mt-5">
                    <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-2">
                      Top Themes
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {patient.topThemes.map((theme) => (
                        <span
                          key={theme}
                          className="px-3 py-1 text-xs rounded-lg bg-muted/60 text-muted-foreground"
                        >
                          {theme}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

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

      {/* ===== Diarization Confirmation Modal ===== */}
      <AnimatePresence>
        {pipelineStep === "diarize-confirm" && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-50"
              onClick={() => setPipelineStep("file-ready")}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 10 }}
              transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md px-4"
            >
              <div className="bg-card rounded-2xl border border-border/60 shadow-[0_25px_65px_rgba(0,0,0,0.12)] overflow-hidden">
                <div className="flex justify-end px-5 pt-5">
                  <button
                    onClick={() => setPipelineStep("file-ready")}
                    className="p-1.5 rounded-lg hover:bg-muted transition-colors"
                  >
                    <X className="w-4 h-4 text-muted-foreground" />
                  </button>
                </div>

                <div className="px-6 pb-6 pt-2 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-4">
                    <Mic className="w-6 h-6 text-primary" />
                  </div>

                  <h2 className="text-foreground tracking-tight mb-3">
                    Create Transcript
                  </h2>

                  <div className="bg-muted/40 border border-border/40 rounded-xl px-4 py-3 mb-4 text-left space-y-3">
                    <p className="text-sm text-foreground/90 leading-relaxed">
                      You are about to use AI to diarize and transcribe this audio recording locally on your device.
                    </p>
                    <p className="text-sm text-foreground/90 leading-relaxed">
                      Due to the heavy processing required, it is advised to close out any other applications and ensure your device is connected to power. This may take a while.
                    </p>
                    <p className="text-sm text-foreground/90 leading-relaxed">
                      Now would be a good time to go grab a cup of coffee <Coffee className="w-4 h-4 inline-block -mt-0.5 text-amber-600" />
                    </p>
                  </div>

                  <div className="bg-amber-500/8 border border-amber-500/20 rounded-xl px-4 py-3 mb-6 text-left flex items-start gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-amber-600 dark:text-amber-400 leading-relaxed">
                      Your device may get hot during processing — this is normal and expected.
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setPipelineStep("file-ready")}
                      className="flex-1 px-4 py-2.5 rounded-xl border border-border/60 text-muted-foreground hover:bg-muted/50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={startDiarization}
                      className="flex-1 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
                    >
                      <Zap className="w-3.5 h-3.5" />
                      <span>Continue</span>
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ===== Diarization Processing Animation Modal ===== */}
      <AnimatePresence>
        {pipelineStep === "diarizing" && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 10 }}
              transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm px-4"
            >
              <div className="bg-card rounded-2xl border border-border/60 shadow-[0_25px_65px_rgba(0,0,0,0.12)] overflow-hidden">
                <div className="px-6 py-10 text-center">
                  {/* Animated mic icon */}
                  <div className="relative w-20 h-20 mx-auto mb-6">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary border-r-primary/30"
                    />
                    <motion.div
                      animate={{ rotate: -360 }}
                      transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-1.5 rounded-full border-2 border-transparent border-b-primary/60 border-l-primary/20"
                    />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <motion.div
                        animate={{ scale: [1, 1.1, 1] }}
                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                      >
                        <Mic className="w-8 h-8 text-primary" />
                      </motion.div>
                    </div>
                  </div>

                  <h2 className="text-foreground tracking-tight mb-1">
                    Creating Transcript
                  </h2>
                  <p className="text-xs text-muted-foreground mb-6">
                    Diarizing audio and separating speakers...
                  </p>

                  {/* Elapsed time */}
                  <div className="flex items-center justify-center gap-1.5 text-muted-foreground">
                    <Clock className="w-3.5 h-3.5" />
                    <span className="text-sm tabular-nums">{formatElapsed(diarizeElapsed)}</span>
                    <span className="text-xs text-muted-foreground/60 ml-1">elapsed</span>
                  </div>

                  {/* Animated status messages */}
                  <div className="mt-5 h-5">
                    <AnimatePresence mode="wait">
                      <motion.p
                        key={Math.floor(diarizeElapsed / 2)}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -6 }}
                        transition={{ duration: 0.3 }}
                        className="text-[11px] text-primary/70"
                      >
                        {[
                          "Loading diarization model...",
                          "Decoding audio waveform...",
                          "Detecting voice activity...",
                          "Segmenting speaker turns...",
                          "Running speech-to-text...",
                          "Aligning speaker labels...",
                        ][Math.floor(diarizeElapsed / 2) % 6]}
                      </motion.p>
                    </AnimatePresence>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ===== BERT Processing Confirmation Modal ===== */}
      <AnimatePresence>
        {pipelineStep === "bert-confirm" && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-50"
              onClick={() => setPipelineStep("speaker-mapping")}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 10 }}
              transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md px-4"
            >
              <div className="bg-card rounded-2xl border border-border/60 shadow-[0_25px_65px_rgba(0,0,0,0.12)] overflow-hidden">
                <div className="flex justify-end px-5 pt-5">
                  <button
                    onClick={() => setPipelineStep("speaker-mapping")}
                    className="p-1.5 rounded-lg hover:bg-muted transition-colors"
                  >
                    <X className="w-4 h-4 text-muted-foreground" />
                  </button>
                </div>

                <div className="px-6 pb-6 pt-2 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-4">
                    <Brain className="w-6 h-6 text-primary" />
                  </div>

                  <h2 className="text-foreground tracking-tight mb-3">
                    Process with BERT
                  </h2>

                  <div className="bg-muted/40 border border-border/40 rounded-xl px-4 py-3 mb-4 text-left space-y-3">
                    <p className="text-sm text-foreground/90 leading-relaxed">
                      You are about to use AI to process patient data locally on your device and update the knowledge graph.
                    </p>
                    <p className="text-sm text-foreground/90 leading-relaxed">
                      Due to the heavy processing of AI, it is advised to close out any other applications and ensure your device is connected to power. This may take a while.
                    </p>
                    <p className="text-sm text-foreground/90 leading-relaxed">
                      Now would be a good time to go grab a cup of coffee <Coffee className="w-4 h-4 inline-block -mt-0.5 text-amber-600" />
                    </p>
                  </div>

                  <div className="bg-amber-500/8 border border-amber-500/20 rounded-xl px-4 py-3 mb-6 text-left flex items-start gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-amber-600 dark:text-amber-400 leading-relaxed">
                      Your device may get hot during processing — this is normal and expected.
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setPipelineStep("speaker-mapping")}
                      className="flex-1 px-4 py-2.5 rounded-xl border border-border/60 text-muted-foreground hover:bg-muted/50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={startBertProcessing}
                      className="flex-1 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
                    >
                      <Zap className="w-3.5 h-3.5" />
                      <span>Continue</span>
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ===== BERT Processing Animation Modal ===== */}
      <AnimatePresence>
        {pipelineStep === "bert-processing" && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 10 }}
              transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm px-4"
            >
              <div className="bg-card rounded-2xl border border-border/60 shadow-[0_25px_65px_rgba(0,0,0,0.12)] overflow-hidden">
                <div className="px-6 py-10 text-center">
                  {/* Animated brain icon */}
                  <div className="relative w-20 h-20 mx-auto mb-6">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary border-r-primary/30"
                    />
                    <motion.div
                      animate={{ rotate: -360 }}
                      transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-1.5 rounded-full border-2 border-transparent border-b-primary/60 border-l-primary/20"
                    />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <motion.div
                        animate={{ scale: [1, 1.1, 1] }}
                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                      >
                        <Brain className="w-8 h-8 text-primary" />
                      </motion.div>
                    </div>
                  </div>

                  <h2 className="text-foreground tracking-tight mb-1">
                    Processing with BERT
                  </h2>
                  <p className="text-xs text-muted-foreground mb-6">
                    Extracting knowledge graph from transcript...
                  </p>

                  {/* Elapsed time */}
                  <div className="flex items-center justify-center gap-1.5 text-muted-foreground">
                    <Clock className="w-3.5 h-3.5" />
                    <span className="text-sm tabular-nums">{formatElapsed(bertElapsed)}</span>
                    <span className="text-xs text-muted-foreground/60 ml-1">elapsed</span>
                  </div>

                  {/* Animated status messages */}
                  <div className="mt-5 h-5">
                    <AnimatePresence mode="wait">
                      <motion.p
                        key={Math.floor(bertElapsed / 3)}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -6 }}
                        transition={{ duration: 0.3 }}
                        className="text-[11px] text-primary/70"
                      >
                        {[
                          "Initializing BERT model...",
                          "Tokenizing transcript...",
                          "Running entity extraction...",
                          "Building knowledge graph edges...",
                          "Analyzing semantic relationships...",
                          "Optimizing graph structure...",
                        ][Math.floor(bertElapsed / 3) % 6]}
                      </motion.p>
                    </AnimatePresence>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ===== Processing Complete Modal ===== */}
      <AnimatePresence>
        {pipelineStep === "complete" && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-50"
              onClick={() => resetPipeline()}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 10 }}
              transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm px-4"
            >
              <div className="bg-card rounded-2xl border border-border/60 shadow-[0_25px_65px_rgba(0,0,0,0.12)] overflow-hidden">
                <div className="px-6 py-10 text-center">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 400, damping: 20, delay: 0.1 }}
                    className="w-14 h-14 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center mx-auto mb-4"
                  >
                    <Check className="w-6 h-6 text-green-500" />
                  </motion.div>

                  <h2 className="text-foreground tracking-tight mb-2">
                    Processing Complete
                  </h2>
                  <p className="text-sm text-foreground/80 mb-3 leading-relaxed">
                    The knowledge graph has been updated to reflect the new session data.
                  </p>
                  <div className="flex items-center justify-center gap-2 mb-6">
                    <Share2 className="w-3.5 h-3.5 text-primary/60" />
                    <p className="text-xs text-muted-foreground">
                      New nodes and relationships have been integrated
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground/50 mb-6">
                    Completed in {Math.floor(bertElapsed / 60)}m {bertElapsed % 60}s
                  </p>

                  <button
                    onClick={() => resetPipeline()}
                    className="px-6 py-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                  >
                    Done
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ===== Delete Session Confirmation Modal ===== */}
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
              transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
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
                      <span className="font-semibold">This action is permanent and cannot be undone.</span>{" "}
                      The selected session transcript and its raw audio data will be irreversibly erased from this device.
                    </p>
                  </div>

                  <div className="bg-primary/6 border border-primary/20 rounded-xl px-4 py-3 mb-6 text-left flex items-start gap-2.5">
                    <Share2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-primary/80 leading-relaxed">
                      The patient's knowledge graph will <span className="font-semibold">not</span> be affected.
                      All previously extracted nodes, edges, and relationships will remain intact.
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
    </div>
  );
}


