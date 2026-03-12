import { useState, useRef, useEffect } from "react";
import {
  Brain,
  Clock,
  FileText,
  MoreHorizontal,
  ChevronRight,
  Trash2,
  GripVertical,
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useDrag, useDrop } from "react-dnd";
import { Patient } from "../context/patient-context";
export type { Patient } from "../context/patient-context";

const DRAG_TYPE = "PATIENT_CARD";

interface DragItem {
  id: string;
  index: number;
}

export interface PatientCardProps {
  patient: Patient;
  index: number;
  onDelete: (id: string) => void;
  onMove: (dragIndex: number, hoverIndex: number) => void;
  onClick?: () => void;
}

export function PatientCard({ patient, index, onDelete, onMove, onClick }: PatientCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
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

  // Drag source
  const [{ isDragging }, dragRef, dragPreview] = useDrag<DragItem, void, { isDragging: boolean }>({
    type: DRAG_TYPE,
    item: { id: patient.id, index },
    collect: (monitor) => ({ isDragging: monitor.isDragging() }),
  });

  // Drop target — reorder on hover
  const [{ isOver }, dropRef] = useDrop<DragItem, void, { isOver: boolean }>({
    accept: DRAG_TYPE,
    collect: (monitor) => ({ isOver: monitor.isOver() }),
    hover(item, monitor) {
      if (!cardRef.current) return;
      const dragIndex = item.index;
      const hoverIndex = index;
      if (dragIndex === hoverIndex) return;

      const hoverBoundingRect = cardRef.current.getBoundingClientRect();
      const hoverMiddleY = (hoverBoundingRect.bottom - hoverBoundingRect.top) / 2;
      const clientOffset = monitor.getClientOffset();
      if (!clientOffset) return;
      const hoverClientY = clientOffset.y - hoverBoundingRect.top;

      // Only move when crossing the midpoint
      if (dragIndex < hoverIndex && hoverClientY < hoverMiddleY) return;
      if (dragIndex > hoverIndex && hoverClientY > hoverMiddleY) return;

      onMove(dragIndex, hoverIndex);
      item.index = hoverIndex;
    },
  });

  // Attach both drag preview and drop to the card, drag handle separately
  dragPreview(dropRef(cardRef));

  return (
    <div
      ref={cardRef}
      style={{ opacity: isDragging ? 0.35 : 1 }}
      className="transition-opacity duration-150"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: index * 0.06, ease: [0.25, 0.46, 0.45, 0.94] }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => {
          if (!isDragging && !menuOpen && onClick) onClick();
        }}
        className={`group relative bg-card rounded-2xl border pl-9 pr-6 pt-5 pb-6 cursor-pointer transition-all duration-200
          ${isOver && !isDragging
            ? "border-primary/50 shadow-[0_0_0_2px_rgba(14,165,160,0.15)]"
            : "border-border/60 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] hover:border-primary/20"
          }`}
      >
        {/* Top accent line */}
        <div
          className="absolute top-0 left-8 right-8 h-[2px] rounded-b-full opacity-60 group-hover:opacity-100 transition-opacity duration-300"
          style={{ backgroundColor: patient.accentColor }}
        />

        {/* Header */}
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-center gap-3">
            {/* Drag handle */}
            <div
              ref={dragRef as unknown as React.RefObject<HTMLDivElement>}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 p-1 opacity-0 group-hover:opacity-40 hover:!opacity-80 transition-opacity cursor-grab active:cursor-grabbing"
              title="Drag to reorder"
            >
              <GripVertical className="w-3.5 h-3.5 text-muted-foreground" />
            </div>

            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-white text-sm tracking-wide"
              style={{ backgroundColor: patient.accentColor }}
            >
              {patient.initials}
            </div>
            <div>
              <h3 className="text-foreground tracking-tight">{patient.name}</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Age {patient.age} &middot; {patient.sessionsCompleted} sessions
              </p>
            </div>
          </div>

          {/* 3-dot menu */}
          <div ref={menuRef} className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setMenuOpen((o) => !o); }}
              className="p-1.5 rounded-lg hover:bg-muted transition-colors opacity-0 group-hover:opacity-100"
            >
              <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
            </button>

            <AnimatePresence>
              {menuOpen && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: -4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: -4 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  className="absolute right-0 top-8 z-20 w-44 bg-card border border-border/60 rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.1)] overflow-hidden"
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuOpen(false);
                      onDelete(patient.id);
                    }}
                    className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-destructive hover:bg-destructive/8 transition-colors text-left"
                  >
                    <Trash2 className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="text-sm">Delete Patient</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Knowledge Graph Mini Viz */}
        <div className="bg-secondary/50 rounded-xl p-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs text-muted-foreground tracking-wide uppercase">
              Knowledge Graph
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xl text-foreground tabular-nums">{patient.graphNodes}</p>
              <p className="text-[11px] text-muted-foreground">Nodes</p>
            </div>
            <div className="w-px h-8 bg-border" />
            <div>
              <p className="text-xl text-foreground tabular-nums">{patient.graphEdges}</p>
              <p className="text-[11px] text-muted-foreground">Edges</p>
            </div>
          </div>
        </div>

        {/* Themes */}
        <div className="flex flex-wrap gap-1.5 mb-5">
          {patient.topThemes.slice(0, 3).map((theme) => (
            <span
              key={theme}
              className="px-2 py-0.5 text-[11px] rounded-md bg-muted/60 text-muted-foreground"
            >
              {theme}
            </span>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-border/40">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Clock className="w-3 h-3" />
            <span className="text-[11px]">Last: {patient.lastSession}</span>
          </div>
          <div className="flex items-center gap-3 text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <FileText className="w-3 h-3" />
              <span className="text-[11px]">Next: {patient.nextSession}</span>
            </div>
            {/* Inline hover CTA — never overlaps text */}
            <motion.div
              initial={false}
              animate={{
                opacity: isHovered && !isDragging ? 1 : 0,
                x: isHovered && !isDragging ? 0 : -4,
              }}
              transition={{ duration: 0.2 }}
              className="pointer-events-none"
            >
              <ChevronRight className="w-4 h-4 text-primary" />
            </motion.div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}