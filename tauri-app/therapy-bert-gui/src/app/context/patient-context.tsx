import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";
import { PatientService } from "../services/patient-service";

export interface Patient {
  id: string;
  name: string;
  initials: string;
  sessionsCompleted: number;
  lastSession: string;
  accentColor: string;
}

const ACCENT_COLORS = [
  "#0ea5a0",
  "#6366f1",
  "#f59e0b",
  "#ec4899",
  "#8b5cf6",
  "#14b8a6",
  "#f97316",
  "#06b6d4",
  "#84cc16",
  "#e11d48",
];

function formatLastSession(isoDate: string | null): string {
  if (!isoDate) return "—";
  try {
    const d = new Date(isoDate);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return "—";
  }
}

function getInitials(name: string): string {
  const names = name.trim().split(/\s+/);
  if (names.length >= 2) {
    return `${names[0][0]}${names[names.length - 1][0]}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase() || "—";
}

interface PatientContextValue {
  patients: Patient[];
  setPatients: React.Dispatch<React.SetStateAction<Patient[]>>;
  addPatient: (data: { name: string }) => Promise<void>;
  deletePatient: (id: string) => void;
  movePatient: (dragIndex: number, hoverIndex: number) => void;
  isDark: boolean;
  toggleDark: () => void;
  patientsLoading: boolean;
  patientsError: string | null;
  refetchPatients: () => Promise<void>;
}

const PatientContext = createContext<PatientContextValue | null>(null);

export function PatientProvider({ children }: { children: ReactNode }) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [patientsError, setPatientsError] = useState<string | null>(null);
  const [isDark, setIsDark] = useState(false);

  const fetchPatients = useCallback(async () => {
    setPatientsLoading(true);
    setPatientsError(null);
    try {
      const data = await PatientService.getPatients();
      const mapped: Patient[] = data.map((p, i) => ({
        id: p.id,
        name: p.name,
        initials: getInitials(p.name),
        sessionsCompleted: p.session_count,
        lastSession: formatLastSession(p.last_session),
        accentColor: ACCENT_COLORS[i % ACCENT_COLORS.length],
      }));
      setPatients(mapped);
    } catch (e) {
      setPatientsError(e instanceof Error ? e.message : "Failed to load patients");
      setPatients([]);
    } finally {
      setPatientsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  const toggleDark = useCallback(() => setIsDark((d) => !d), []);

  const addPatient = useCallback(
    async (data: { name: string }) => {
      setPatientsError(null);
      try {
        const created = await PatientService.createPatient(data.name);
        const newPatient: Patient = {
          id: created.id,
          name: created.name,
          initials: getInitials(created.name),
          sessionsCompleted: 0,
          lastSession: "—",
          accentColor: ACCENT_COLORS[patients.length % ACCENT_COLORS.length],
        };
        setPatients((prev) => [newPatient, ...prev]);
      } catch (e) {
        setPatientsError(e instanceof Error ? e.message : "Failed to add patient");
        throw e;
      }
    },
    [patients.length]
  );

  const deletePatient = useCallback(async (id: string) => {
    setPatientsError(null);
    try {
      await PatientService.deletePatient(id);
      setPatients((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      setPatientsError(e instanceof Error ? e.message : "Failed to delete patient");
      throw e;
    }
  }, []);

  const movePatient = useCallback((dragIndex: number, hoverIndex: number) => {
    setPatients((prev) => {
      const updated = [...prev];
      const [removed] = updated.splice(dragIndex, 1);
      updated.splice(hoverIndex, 0, removed);
      return updated;
    });
  }, []);

  return (
    <PatientContext.Provider
      value={{
        patients,
        setPatients,
        addPatient,
        deletePatient,
        movePatient,
        isDark,
        toggleDark,
        patientsLoading,
        patientsError,
        refetchPatients: fetchPatients,
      }}
    >
      {children}
    </PatientContext.Provider>
  );
}

export function usePatients() {
  const ctx = useContext(PatientContext);
  if (!ctx) throw new Error("usePatients must be used within PatientProvider");
  return ctx;
}
