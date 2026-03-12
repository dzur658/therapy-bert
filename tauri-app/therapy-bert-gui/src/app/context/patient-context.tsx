import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";

export interface Patient {
  id: string;
  name: string;
  initials: string;
  age: number;
  sessionsCompleted: number;
  lastSession: string;
  nextSession: string;
  graphNodes: number;
  graphEdges: number;
  topThemes: string[];
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

const initialPatients: Patient[] = [
  {
    id: "1",
    name: "Sarah Mitchell",
    initials: "SM",
    age: 34,
    sessionsCompleted: 24,
    lastSession: "Mar 9",
    nextSession: "Mar 14",
    graphNodes: 187,
    graphEdges: 312,
    topThemes: ["Anxiety", "Work Stress", "Self-Esteem"],
    accentColor: ACCENT_COLORS[0],
  },
  {
    id: "2",
    name: "James Rivera",
    initials: "JR",
    age: 28,
    sessionsCompleted: 12,
    lastSession: "Mar 7",
    nextSession: "Mar 16",
    graphNodes: 94,
    graphEdges: 158,
    topThemes: ["Grief", "Family Dynamics", "Coping"],
    accentColor: ACCENT_COLORS[1],
  },
  {
    id: "3",
    name: "Amara Chen",
    initials: "AC",
    age: 41,
    sessionsCompleted: 38,
    lastSession: "Mar 10",
    nextSession: "Mar 12",
    graphNodes: 342,
    graphEdges: 578,
    topThemes: ["PTSD", "Relationships", "Resilience"],
    accentColor: ACCENT_COLORS[2],
  },
  {
    id: "4",
    name: "David Okafor",
    initials: "DO",
    age: 52,
    sessionsCompleted: 8,
    lastSession: "Mar 5",
    nextSession: "Mar 18",
    graphNodes: 56,
    graphEdges: 87,
    topThemes: ["Depression", "Isolation", "Sleep"],
    accentColor: ACCENT_COLORS[3],
  },
  {
    id: "5",
    name: "Elena Vasquez",
    initials: "EV",
    age: 29,
    sessionsCompleted: 16,
    lastSession: "Mar 8",
    nextSession: "Mar 15",
    graphNodes: 128,
    graphEdges: 214,
    topThemes: ["Identity", "Career", "Mindfulness"],
    accentColor: ACCENT_COLORS[4],
  },
  {
    id: "6",
    name: "Marcus Webb",
    initials: "MW",
    age: 45,
    sessionsCompleted: 31,
    lastSession: "Mar 6",
    nextSession: "Mar 13",
    graphNodes: 265,
    graphEdges: 421,
    topThemes: ["Anger", "Communication", "Boundaries"],
    accentColor: ACCENT_COLORS[5],
  },
];

interface PatientContextValue {
  patients: Patient[];
  setPatients: React.Dispatch<React.SetStateAction<Patient[]>>;
  addPatient: (data: { name: string; age: number; notes: string }) => void;
  deletePatient: (id: string) => void;
  movePatient: (dragIndex: number, hoverIndex: number) => void;
  isDark: boolean;
  toggleDark: () => void;
}

const PatientContext = createContext<PatientContextValue | null>(null);

export function PatientProvider({ children }: { children: ReactNode }) {
  const [patients, setPatients] = useState<Patient[]>(initialPatients);
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  const toggleDark = useCallback(() => setIsDark((d) => !d), []);

  const addPatient = useCallback(
    (data: { name: string; age: number; notes: string }) => {
      const names = data.name.split(" ");
      const initials =
        names.length >= 2
          ? `${names[0][0]}${names[names.length - 1][0]}`.toUpperCase()
          : data.name.slice(0, 2).toUpperCase();

      const newPatient: Patient = {
        id: Date.now().toString(),
        name: data.name,
        initials,
        age: data.age,
        sessionsCompleted: 0,
        lastSession: "N/A",
        nextSession: "TBD",
        graphNodes: 0,
        graphEdges: 0,
        topThemes: [],
        accentColor: ACCENT_COLORS[patients.length % ACCENT_COLORS.length],
      };
      setPatients((prev) => [newPatient, ...prev]);
    },
    [patients.length]
  );

  const deletePatient = useCallback((id: string) => {
    setPatients((prev) => prev.filter((p) => p.id !== id));
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
      value={{ patients, setPatients, addPatient, deletePatient, movePatient, isDark, toggleDark }}
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
