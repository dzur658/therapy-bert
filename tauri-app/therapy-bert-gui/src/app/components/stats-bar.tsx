import { motion } from "motion/react";
import { Users, Brain, FileText } from "lucide-react";

interface StatsBarProps {
  totalPatients: number;
  totalNodes: number;
  totalSessions: number;
}

export function StatsBar({ totalPatients, totalNodes, totalSessions }: StatsBarProps) {
  const stats = [
    { label: "Patients", value: totalPatients, icon: Users, color: "text-primary" },
    { label: "Graph Nodes", value: totalNodes.toLocaleString(), icon: Brain, color: "text-violet-500" },
    { label: "Total Sessions", value: totalSessions, icon: FileText, color: "text-amber-500" },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-8"
    >
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-card rounded-xl border border-border/60 px-4 py-3.5 flex items-center gap-3"
        >
          <div className="w-9 h-9 rounded-lg bg-secondary/80 flex items-center justify-center">
            <stat.icon className={`w-4 h-4 ${stat.color}`} />
          </div>
          <div>
            <p className="text-lg text-foreground tabular-nums">{stat.value}</p>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider">{stat.label}</p>
          </div>
        </div>
      ))}
    </motion.div>
  );
}