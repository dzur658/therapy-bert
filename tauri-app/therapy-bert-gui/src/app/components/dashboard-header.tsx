import { Plus, Search, Brain, Sun, Moon } from "lucide-react";
import { motion } from "motion/react";

interface DashboardHeaderProps {
  patientCount: number;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onNewPatient: () => void;
  isDark: boolean;
  onToggleDark: () => void;
}

export function DashboardHeader({
  patientCount,
  searchQuery,
  onSearchChange,
  onNewPatient,
  isDark,
  onToggleDark,
}: DashboardHeaderProps) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8"
    >
      {/* Left - Branding */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-sm">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-foreground tracking-tight flex items-center gap-2">
            Therapy
            <span className="text-primary">BERT</span>
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {patientCount} active patient{patientCount !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Right - Search + Dark Mode + Add */}
      <div className="flex items-center gap-3 w-full sm:w-auto">
        <div className="relative flex-1 sm:flex-initial">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/60" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search patients..."
            className="w-full sm:w-56 pl-9 pr-4 py-2 rounded-xl bg-card border border-border/60 text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
          />
        </div>

        {/* Dark mode toggle */}
        <button
          onClick={onToggleDark}
          aria-label="Toggle dark mode"
          className="relative w-[52px] h-[28px] rounded-full border border-border/60 bg-card transition-colors duration-300 flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-primary/30"
        >
          {/* Track fill */}
          <span
            className="absolute inset-0 rounded-full transition-colors duration-300"
            style={{ backgroundColor: isDark ? "rgba(14,165,160,0.2)" : "transparent" }}
          />
          {/* Icons */}
          <Sun className="absolute left-[6px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-amber-400 transition-opacity duration-200"
            style={{ opacity: isDark ? 0.3 : 1 }} />
          <Moon className="absolute right-[6px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-primary transition-opacity duration-200"
            style={{ opacity: isDark ? 1 : 0.3 }} />
          {/* Thumb */}
          <motion.span
            animate={{ x: isDark ? 24 : 2 }}
            transition={{ type: "spring", stiffness: 500, damping: 35 }}
            className="absolute top-[3px] w-[22px] h-[22px] rounded-full bg-primary shadow-sm"
            style={{ left: 0 }}
          />
        </button>

        <button
          onClick={onNewPatient}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm hover:shadow-md active:scale-[0.98]"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">New Patient</span>
        </button>
      </div>
    </motion.header>
  );
}