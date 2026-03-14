import { useRef, useEffect, useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Info,
  Search,
  X,
  ArrowRight,
  ArrowLeft,
  Send,
  Bot,
  User,
  Loader2,
  Sparkles,
  MessageSquare,
  ChevronRight,
} from "lucide-react";

// ── LadybugDB Schema Types ──────────────────────────────────────────────────
export interface GraphEntity {
  text: string;
  label: string;
}

export interface GraphRelation {
  source: string;
  target: string;
  predicate: string;
  proposed_by: string;
  patient_acceptance: string;
}

export interface KnowledgeGraphData {
  entities: GraphEntity[];
  relations: GraphRelation[];
}

// ── Color mapping per entity label ──────────────────────────────────────────
const LABEL_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  EMOTION:   { fill: "#ef4444", stroke: "#dc2626", text: "#fef2f2" },
  PERSON:    { fill: "#6366f1", stroke: "#4f46e5", text: "#eef2ff" },
  BEHAVIOR:  { fill: "#f59e0b", stroke: "#d97706", text: "#fefce8" },
  THEME:     { fill: "#0ea5a0", stroke: "#0d9488", text: "#f0fdfa" },
  CONCEPT:   { fill: "#8b5cf6", stroke: "#7c3aed", text: "#f5f3ff" },
  EVENT:     { fill: "#ec4899", stroke: "#db2777", text: "#fdf2f8" },
  SYMPTOM:   { fill: "#f97316", stroke: "#ea580c", text: "#fff7ed" },
  STRATEGY:  { fill: "#14b8a6", stroke: "#0d9488", text: "#f0fdfa" },
  TRIGGER:   { fill: "#e11d48", stroke: "#be123c", text: "#fff1f2" },
  GOAL:      { fill: "#84cc16", stroke: "#65a30d", text: "#f7fee7" },
};

const DEFAULT_COLOR = { fill: "#64748b", stroke: "#475569", text: "#f8fafc" };

function getColor(label: string) {
  return LABEL_COLORS[label] || DEFAULT_COLOR;
}

function getAcceptanceColor(acceptance: string): string {
  switch (acceptance) {
    case "accepted": return "#22c55e";
    case "pending":  return "#f59e0b";
    case "rejected": return "#ef4444";
    default:         return "#64748b";
  }
}

// ── Simulation types ────────────────────────────────────────────────────────
interface SimNode {
  id: string;
  label: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  pinned: boolean;
}

interface SimEdge {
  source: string;
  target: string;
  predicate: string;
  proposed_by: string;
  patient_acceptance: string;
}

const MAX_SIM_ITERS = 350;
const POST_DRAG_ITERS = 150;

// ── AI Chat types ───────────────────────────────────────────────────────────
interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const GRAPH_RAG_API_BASE = "http://127.0.0.1:8091";

// ── Component ────────────────────────────────────────────────────────────────
export function KnowledgeGraph({
  data,
  accentColor,
  patientName,
  patientId,
}: {
  data: KnowledgeGraphData;
  accentColor: string;
  patientName: string;
  patientId: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const edgesRef = useRef<SimEdge[]>([]);
  const iterRef = useRef(0);
  const simulatingUntil = useRef(MAX_SIM_ITERS);
  const animRef = useRef<number>(0);
  const draggingNode = useRef<SimNode | null>(null);
  const wasDragging = useRef(false);

  // Reactive state
  const [, forceRender] = useState(0);
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<SimEdge | null>(null);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);
  const isPanning = useRef(false);
  const lastMouse = useRef({ x: 0, y: 0 });

  // Chat state
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isAiTyping, setIsAiTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatSessionIdRef = useRef<string>(crypto.randomUUID());

  // Sidebar state
  const sidebarOpen = selectedNode !== null || selectedEdge !== null;

  const W = 800, H = 500;

  // Derived
  const uniqueLabels = useMemo(
    () => [...new Set(data.entities.map((e) => e.label))].sort(),
    [data.entities]
  );

  const matchedNodeIds = useMemo<Set<string> | null>(() => {
    if (!searchQuery.trim()) return null;
    const q = searchQuery.toLowerCase();
    return new Set(
      data.entities.filter((e) => e.text.toLowerCase().includes(q)).map((e) => e.text)
    );
  }, [searchQuery, data.entities]);

  const selectedNodeOutgoing = useMemo(
    () => (selectedNode ? data.relations.filter((r) => r.source === selectedNode.id) : []),
    [selectedNode, data.relations]
  );
  const selectedNodeIncoming = useMemo(
    () => (selectedNode ? data.relations.filter((r) => r.target === selectedNode.id) : []),
    [selectedNode, data.relations]
  );

  const selectedEdgeSourceNode = useMemo(
    () => selectedEdge ? nodesRef.current.find(n => n.id === selectedEdge.source) : null,
    [selectedEdge]
  );
  const selectedEdgeTargetNode = useMemo(
    () => selectedEdge ? nodesRef.current.find(n => n.id === selectedEdge.target) : null,
    [selectedEdge]
  );

  // ── Initialise nodes & edges whenever data changes ──────────────────────
  useEffect(() => {
    const cx = W / 2, cy = H / 2;
    const deg: Record<string, number> = {};
    data.entities.forEach((e) => (deg[e.text] = 0));
    data.relations.forEach((r) => {
      deg[r.source] = (deg[r.source] || 0) + 1;
      deg[r.target] = (deg[r.target] || 0) + 1;
    });
    const maxDeg = Math.max(1, ...Object.values(deg));

    nodesRef.current = data.entities.map((entity, i) => {
      const angle = (i / data.entities.length) * Math.PI * 2;
      const spread = 150 + Math.random() * 100;
      const conn = deg[entity.text] || 0;
      const radius = 8 + (conn / maxDeg) * 16;
      return {
        id: entity.text,
        label: entity.label,
        x: cx + Math.cos(angle) * spread + (Math.random() - 0.5) * 40,
        y: cy + Math.sin(angle) * spread + (Math.random() - 0.5) * 40,
        vx: 0, vy: 0, radius,
        pinned: false,
      };
    });

    edgesRef.current = data.relations.map((r) => ({
      source: r.source,
      target: r.target,
      predicate: r.predicate,
      proposed_by: r.proposed_by,
      patient_acceptance: r.patient_acceptance,
    }));

    iterRef.current = 0;
    simulatingUntil.current = MAX_SIM_ITERS;
    setSelectedNode(null);
    setSelectedEdge(null);
    setSearchQuery("");
    setSelectedLabel(null);
  }, [data]);

  // ── RAF physics loop ─────────────────────────────────────────────────────
  useEffect(() => {
    const cx = W / 2, cy = H / 2;

    function simulate() {
      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      const nodeMap = new Map<string, SimNode>();
      nodes.forEach((n) => nodeMap.set(n.id, n));

      let cooling: number;
      if (iterRef.current < MAX_SIM_ITERS) {
        cooling = Math.max(0.005, 1 - iterRef.current / MAX_SIM_ITERS);
      } else {
        cooling = 0.12;
      }
      iterRef.current++;

      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].pinned) continue;
        nodes[i].vx += (cx - nodes[i].x) * 0.0005;
        nodes[i].vy += (cy - nodes[i].y) * 0.0005;
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const f = (800 / (dist * dist)) * cooling;
          const fx = (dx / dist) * f;
          const fy = (dy / dist) * f;
          if (!nodes[i].pinned) { nodes[i].vx += fx; nodes[i].vy += fy; }
          if (!nodes[j].pinned) { nodes[j].vx -= fx; nodes[j].vy -= fy; }
        }
      }

      edges.forEach((e) => {
        const s = nodeMap.get(e.source);
        const t = nodeMap.get(e.target);
        if (!s || !t) return;
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const f = (dist - 120) * 0.003 * cooling;
        const fx = (dx / dist) * f;
        const fy = (dy / dist) * f;
        if (!s.pinned) { s.vx += fx; s.vy += fy; }
        if (!t.pinned) { t.vx -= fx; t.vy -= fy; }
      });

      nodes.forEach((n) => {
        if (n.pinned) return;
        n.vx *= 0.85; n.vy *= 0.85;
        n.x += n.vx; n.y += n.vy;
        n.x = Math.max(n.radius + 20, Math.min(W - n.radius - 20, n.x));
        n.y = Math.max(n.radius + 20, Math.min(H - n.radius - 20, n.y));
      });
    }

    function frame() {
      if (iterRef.current < simulatingUntil.current) {
        simulate();
        forceRender(c => c + 1);
      }
      animRef.current = requestAnimationFrame(frame);
    }

    animRef.current = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(animRef.current);
  }, [data]);

  // ── SVG coordinate helpers ───────────────────────────────────────────────
  const getSvgPos = useCallback(
    (e: React.MouseEvent): { x: number; y: number } => {
      const rect = containerRef.current?.querySelector("svg")?.getBoundingClientRect();
      if (!rect) return { x: 0, y: 0 };
      return {
        x: (e.clientX - rect.left - pan.x) / zoom,
        y: (e.clientY - rect.top - pan.y) / zoom,
      };
    },
    [zoom, pan]
  );

  // ── Mouse handlers ────────────────────────────────────────────────────────
  const handleSvgMouseDown = useCallback((e: React.MouseEvent) => {
    wasDragging.current = false;
    isPanning.current = true;
    lastMouse.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleSvgMouseMove = useCallback((e: React.MouseEvent) => {
    if (draggingNode.current) {
      wasDragging.current = true;
      const pos = getSvgPos(e);
      draggingNode.current.x = pos.x;
      draggingNode.current.y = pos.y;
      forceRender(c => c + 1);
      return;
    }
    if (isPanning.current) {
      const dx = e.clientX - lastMouse.current.x;
      const dy = e.clientY - lastMouse.current.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) wasDragging.current = true;
      setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
      lastMouse.current = { x: e.clientX, y: e.clientY };
    }
  }, [getSvgPos]);

  const handleSvgMouseUp = useCallback(() => {
    if (draggingNode.current) {
      draggingNode.current.pinned = false;
      simulatingUntil.current = iterRef.current + POST_DRAG_ITERS;
      draggingNode.current = null;
    }
    isPanning.current = false;
  }, []);

  const handleSvgMouseLeave = useCallback(() => {
    if (draggingNode.current) {
      draggingNode.current.pinned = false;
      simulatingUntil.current = iterRef.current + POST_DRAG_ITERS;
      draggingNode.current = null;
    }
    isPanning.current = false;
    wasDragging.current = false;
    setHoveredNode(null);
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => Math.max(0.3, Math.min(3, z * (e.deltaY > 0 ? 0.92 : 1.08))));
  }, []);

  const resetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const handleNodeMouseDown = useCallback((node: SimNode, e: React.MouseEvent) => {
    e.stopPropagation();
    wasDragging.current = false;
    draggingNode.current = node;
    node.pinned = true;
    lastMouse.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleNodeClick = useCallback((node: SimNode) => {
    if (wasDragging.current) return;
    setSelectedEdge(null);
    setSelectedNode((prev) => (prev?.id === node.id ? null : node));
  }, []);

  const handleEdgeClick = useCallback((edge: SimEdge, e: React.MouseEvent) => {
    e.stopPropagation();
    if (wasDragging.current) return;
    setSelectedNode(null);
    setSelectedEdge((prev) =>
      prev?.source === edge.source && prev?.target === edge.target && prev?.predicate === edge.predicate
        ? null
        : edge
    );
  }, []);

  const handleSvgClick = useCallback(() => {
    if (wasDragging.current) return;
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  const navigateTo = useCallback((id: string) => {
    const n = nodesRef.current.find((n) => n.id === id);
    if (n) {
      setSelectedEdge(null);
      setSelectedNode(n);
    }
  }, []);

  // ── Chat handlers ─────────────────────────────────────────────────────────
  const sendMessage = useCallback(async () => {
    const text = chatInput.trim();
    if (!text || isAiTyping || !patientId) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput("");
    setIsAiTyping(true);

    const aiMsgId = (Date.now() + 1).toString();
    const aiMsg: ChatMessage = {
      id: aiMsgId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
    };
    setChatMessages(prev => [...prev, aiMsg]);

    try {
      const res = await fetch(`${GRAPH_RAG_API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: chatSessionIdRef.current,
          patient_id: patientId,
          message: text,
        }),
      });

      if (!res.ok) {
        const errText = await res.text().catch(() => "");
        throw new Error(errText || `Graph RAG API error: ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulated += chunk;
        setChatMessages(prev =>
          prev.map(m =>
            m.id === aiMsgId ? { ...m, content: accumulated } : m
          )
        );
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Graph RAG service unavailable";
      setChatMessages(prev =>
        prev.map(m =>
          m.id === aiMsgId
            ? { ...m, content: `Error: ${errMsg}. Please ensure the Graph RAG service is running at ${GRAPH_RAG_API_BASE}.` }
            : m
        )
      );
    } finally {
      setIsAiTyping(false);
    }
  }, [chatInput, isAiTyping, patientId]);

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, isAiTyping]);

  // ── Recenter graph when sidebar opens/closes ──────────────────────────────
  useEffect(() => {
    if (sidebarOpen) {
      setPan((p) => ({ x: p.x - 150, y: p.y }));
    } else {
      setPan((p) => ({ x: p.x + 150, y: p.y }));
    }
  }, [sidebarOpen]);

  // ── Build node map for rendering ──────────────────────────────────────────
  const nodeMap = useMemo(() => {
    const map = new Map<string, SimNode>();
    nodesRef.current.forEach(n => map.set(n.id, n));
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodesRef.current.length, data]);

  const hasSearch = matchedNodeIds !== null;
  const hasLabelFilter = selectedLabel !== null;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div ref={containerRef} className="relative w-full">
      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-shrink-0">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder="Search nodes…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 pr-7 py-1.5 text-xs bg-secondary/50 border border-border/40 rounded-lg w-36 focus:outline-none focus:ring-1 focus:ring-border/60 text-foreground placeholder:text-muted-foreground"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Label filters */}
        <div className="flex items-center gap-1 flex-wrap flex-1">
          <button
            onClick={() => setSelectedLabel(null)}
            className={`px-2.5 py-1 rounded-lg text-[11px] transition-all ${
              selectedLabel === null
                ? "bg-foreground/10 text-foreground"
                : "text-muted-foreground hover:bg-muted/50"
            }`}
          >
            All
          </button>
          {uniqueLabels.map((label) => {
            const color = getColor(label);
            return (
              <button
                key={label}
                onClick={() => setSelectedLabel(selectedLabel === label ? null : label)}
                className={`px-2.5 py-1 rounded-lg text-[11px] transition-all flex items-center gap-1.5 ${
                  selectedLabel === label
                    ? "text-foreground"
                    : "text-muted-foreground hover:bg-muted/50"
                }`}
                style={selectedLabel === label ? { backgroundColor: color.fill + "1a" } : {}}
              >
                <span
                  className="w-2 h-2 rounded-full inline-block flex-shrink-0"
                  style={{ backgroundColor: color.fill }}
                />
                {label}
              </button>
            );
          })}
        </div>

        {/* Zoom controls */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={() => setZoom((z) => Math.min(3, z * 1.2))} className="p-1.5 rounded-lg hover:bg-muted/60 transition-colors" aria-label="Zoom in">
            <ZoomIn className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
          <button onClick={() => setZoom((z) => Math.max(0.3, z * 0.8))} className="p-1.5 rounded-lg hover:bg-muted/60 transition-colors" aria-label="Zoom out">
            <ZoomOut className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
          <button onClick={resetView} className="p-1.5 rounded-lg hover:bg-muted/60 transition-colors" aria-label="Reset view">
            <Maximize2 className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
        </div>
      </div>

      {/* ── Main graph area with sidebar ── */}
      <div className="flex gap-0 rounded-xl overflow-hidden border border-border/40">

        {/* SVG Graph Area */}
        <div className="relative flex-1 bg-secondary/30 overflow-hidden" style={{ minHeight: 460 }}>
          <svg
            width="100%"
            height="460"
            viewBox={`0 0 ${W} ${H}`}
            className="cursor-grab active:cursor-grabbing"
            style={{ cursor: hoveredNode ? "pointer" : undefined }}
            onMouseDown={handleSvgMouseDown}
            onMouseMove={handleSvgMouseMove}
            onMouseUp={handleSvgMouseUp}
            onMouseLeave={handleSvgMouseLeave}
            onWheel={handleWheel}
            onClick={handleSvgClick}
          >
            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              {/* Edges */}
              {edgesRef.current.map((edge, i) => {
                const s = nodeMap.get(edge.source);
                const t = nodeMap.get(edge.target);
                if (!s || !t) return null;

                const isSelEdge = selectedEdge?.source === edge.source &&
                  selectedEdge?.target === edge.target &&
                  selectedEdge?.predicate === edge.predicate;
                const isConnectedToSelectedNode = selectedNode
                  ? edge.source === selectedNode.id || edge.target === selectedNode.id
                  : false;

                let dimmed = false;
                if (hasSearch) {
                  dimmed = !(matchedNodeIds!.has(s.id) || matchedNodeIds!.has(t.id));
                } else if (hasLabelFilter) {
                  dimmed = s.label !== selectedLabel && t.label !== selectedLabel;
                }
                if (selectedNode && !isConnectedToSelectedNode) dimmed = true;
                if (selectedEdge && !isSelEdge) dimmed = true;

                const dashArray = edge.patient_acceptance === "pending" ? "6,4"
                  : edge.patient_acceptance === "rejected" ? "2,4" : undefined;

                const edgeColor = isSelEdge || isConnectedToSelectedNode
                  ? accentColor
                  : dimmed
                  ? "rgba(128,128,128,0.12)"
                  : edge.proposed_by === "patient"
                  ? "rgba(14,165,160,0.5)"
                  : "rgba(139,92,246,0.5)";

                const edgeWidth = isSelEdge ? 3 : isConnectedToSelectedNode ? 2 : 1.2;
                const edgeOpacity = dimmed ? 0.3 : isSelEdge ? 1 : 0.8;

                // Arrowhead
                const dx = t.x - s.x;
                const dy = t.y - s.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const tipX = t.x - (dx / dist) * (t.radius + 3);
                const tipY = t.y - (dy / dist) * (t.radius + 3);
                const ang = Math.atan2(dy, dx);
                const AL = 8, AA = 0.4;

                return (
                  <g key={`edge-${i}`} opacity={edgeOpacity} style={{ pointerEvents: "none" }}>
                    {/* Invisible wider hit area for clicking */}
                    <line
                      x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                      stroke="transparent" strokeWidth={12}
                      style={{ cursor: "pointer", pointerEvents: "auto" }}
                      onClick={(e) => handleEdgeClick(edge, e)}
                    />
                    <line
                      x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                      stroke={edgeColor}
                      strokeWidth={edgeWidth}
                      strokeDasharray={dashArray}
                    />
                    {/* Arrowhead */}
                    {!dimmed && dist > 1 && (
                      <path
                        d={`M ${tipX} ${tipY} L ${tipX - AL * Math.cos(ang - AA)} ${tipY - AL * Math.sin(ang - AA)} M ${tipX} ${tipY} L ${tipX - AL * Math.cos(ang + AA)} ${tipY - AL * Math.sin(ang + AA)}`}
                        stroke={edgeColor}
                        strokeWidth={1.5}
                        fill="none"
                        style={{ pointerEvents: "none" }}
                      />
                    )}
                    {/* Edge predicate label on selection */}
                    {isSelEdge && (
                      <text
                        x={(s.x + t.x) / 2}
                        y={(s.y + t.y) / 2 - 8}
                        textAnchor="middle"
                        fill={accentColor}
                        fontSize={10}
                        fontFamily="system-ui, sans-serif"
                        style={{ pointerEvents: "none" }}
                      >
                        {edge.predicate}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Nodes */}
              {nodesRef.current.map((node) => {
                const color = getColor(node.label);
                const isSel = selectedNode?.id === node.id;
                const isHov = hoveredNode?.id === node.id;
                const isMatch = hasSearch && matchedNodeIds!.has(node.id);

                let dimmed = false;
                if (hasSearch) {
                  dimmed = !isMatch;
                } else if (hasLabelFilter && !isSel) {
                  dimmed = node.label !== selectedLabel;
                }
                if (selectedNode && !isSel) {
                  const isConnected = data.relations.some(
                    r => (r.source === selectedNode.id && r.target === node.id) ||
                         (r.target === selectedNode.id && r.source === node.id)
                  );
                  dimmed = !isConnected;
                }
                if (selectedEdge) {
                  dimmed = node.id !== selectedEdge.source && node.id !== selectedEdge.target;
                }

                const fontSize = Math.max(7, node.radius * 0.65);
                const truncLabel = node.id.length > 14 ? node.id.slice(0, 12) + "…" : node.id;

                return (
                  <g
                    key={node.id}
                    style={{ cursor: "pointer", pointerEvents: "auto" }}
                    onMouseDown={(e) => handleNodeMouseDown(node, e)}
                    onClick={() => handleNodeClick(node)}
                    onMouseEnter={() => setHoveredNode(node)}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    {/* Selection glow */}
                    {(isSel || isMatch) && (
                      <circle
                        cx={node.x} cy={node.y}
                        r={node.radius + (isSel ? 10 : 6)}
                        fill={isSel ? accentColor + "28" : "#fbbf2428"}
                      />
                    )}
                    {/* Selection ring */}
                    {isSel && (
                      <circle
                        cx={node.x} cy={node.y}
                        r={node.radius + 5}
                        fill="none"
                        stroke={accentColor}
                        strokeWidth={2.5}
                      />
                    )}
                    {/* Search match ring */}
                    {isMatch && !isSel && (
                      <circle
                        cx={node.x} cy={node.y}
                        r={node.radius + 2}
                        fill="none"
                        stroke="#fbbf24"
                        strokeWidth={1.5}
                      />
                    )}
                    {/* Node circle */}
                    <circle
                      cx={node.x} cy={node.y}
                      r={node.radius}
                      fill={dimmed ? "rgba(128,128,128,0.15)" : color.fill}
                      stroke={dimmed ? "rgba(128,128,128,0.2)" : color.stroke}
                      strokeWidth={isHov ? 2.5 : 1.5}
                    />
                    {/* Node text */}
                    {(node.radius > 10 || isHov || isSel) && (
                      <text
                        x={node.x} y={node.y}
                        textAnchor="middle"
                        dominantBaseline="central"
                        fill={dimmed ? "rgba(128,128,128,0.3)" : color.text}
                        fontSize={fontSize}
                        fontFamily="system-ui, sans-serif"
                        fontWeight={isHov || isSel ? "bold" : "normal"}
                        style={{ pointerEvents: "none", userSelect: "none" }}
                      >
                        {truncLabel}
                      </text>
                    )}
                    {/* Label badge on hover */}
                    {isHov && !isSel && (
                      <text
                        x={node.x} y={node.y + node.radius + 12}
                        textAnchor="middle"
                        fill={color.fill}
                        fontSize={9}
                        fontFamily="system-ui, sans-serif"
                        style={{ pointerEvents: "none" }}
                      >
                        {node.label}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>

          {/* Search match badge */}
          {searchQuery && matchedNodeIds && (
            <div className="absolute top-3 left-3 text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-lg px-2 py-0.5">
              {matchedNodeIds.size} match{matchedNodeIds.size !== 1 ? "es" : ""}
            </div>
          )}

          {/* Zoom indicator */}
          <div className="absolute bottom-3 right-3 text-[10px] text-muted-foreground/50 bg-card/60 rounded-lg px-2 py-0.5">
            {Math.round(zoom * 100)}%
          </div>
        </div>

        {/* ── Sidebar ── */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 300, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="overflow-hidden border-l border-border/40 bg-card flex-shrink-0"
            >
              <div className="w-[300px] h-[460px] overflow-y-auto">
                {/* Node Sidebar */}
                {selectedNode && (
                  <div>
                    {/* Header */}
                    <div
                      className="px-4 py-4 border-b border-border/40"
                      style={{ borderLeftColor: getColor(selectedNode.label).fill, borderLeftWidth: 3 }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span
                            className="w-3.5 h-3.5 rounded-full flex-shrink-0"
                            style={{ backgroundColor: getColor(selectedNode.label).fill }}
                          />
                          <span className="text-sm text-foreground truncate">{selectedNode.id}</span>
                        </div>
                        <button
                          onClick={() => setSelectedNode(null)}
                          className="p-1 rounded-lg hover:bg-muted/50 transition-colors flex-shrink-0"
                        >
                          <X className="w-3.5 h-3.5 text-muted-foreground" />
                        </button>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className="px-2 py-0.5 rounded text-[10px] uppercase tracking-wider"
                          style={{
                            backgroundColor: getColor(selectedNode.label).fill + "22",
                            color: getColor(selectedNode.label).fill,
                          }}
                        >
                          {selectedNode.label}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {selectedNodeOutgoing.length + selectedNodeIncoming.length} relation{selectedNodeOutgoing.length + selectedNodeIncoming.length !== 1 ? "s" : ""}
                        </span>
                      </div>
                    </div>

                    {/* Outgoing Relations */}
                    <div className="px-4 py-3 border-b border-border/40">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                        <ArrowRight className="w-3 h-3" />
                        Outgoing ({selectedNodeOutgoing.length})
                      </p>
                      {selectedNodeOutgoing.length > 0 ? (
                        <div className="space-y-2.5">
                          {selectedNodeOutgoing.map((e, i) => (
                            <div key={i} className="text-[11px]">
                              <div className="flex items-start gap-1.5">
                                <span
                                  className="w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0"
                                  style={{ backgroundColor: getAcceptanceColor(e.patient_acceptance) }}
                                />
                                <div className="min-w-0">
                                  <span className="text-muted-foreground italic">{e.predicate}</span>
                                  {" → "}
                                  <button
                                    className="text-foreground hover:underline"
                                    onClick={() => navigateTo(e.target)}
                                  >
                                    {e.target}
                                  </button>
                                  <div className="flex items-center gap-1.5 mt-1">
                                    <span
                                      className="px-1.5 py-px rounded text-[9px]"
                                      style={{
                                        backgroundColor: e.proposed_by === "patient" ? "#0ea5a018" : "#8b5cf618",
                                        color: e.proposed_by === "patient" ? "#0ea5a0" : "#8b5cf6",
                                      }}
                                    >
                                      {e.proposed_by}
                                    </span>
                                    <span
                                      className="px-1.5 py-px rounded text-[9px]"
                                      style={{
                                        backgroundColor: getAcceptanceColor(e.patient_acceptance) + "20",
                                        color: getAcceptanceColor(e.patient_acceptance),
                                      }}
                                    >
                                      {e.patient_acceptance}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-[11px] text-muted-foreground italic">No outgoing relations</p>
                      )}
                    </div>

                    {/* Incoming Relations */}
                    <div className="px-4 py-3">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                        <ArrowLeft className="w-3 h-3" />
                        Incoming ({selectedNodeIncoming.length})
                      </p>
                      {selectedNodeIncoming.length > 0 ? (
                        <div className="space-y-2.5">
                          {selectedNodeIncoming.map((e, i) => (
                            <div key={i} className="text-[11px]">
                              <div className="flex items-start gap-1.5">
                                <span
                                  className="w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0"
                                  style={{ backgroundColor: getAcceptanceColor(e.patient_acceptance) }}
                                />
                                <div className="min-w-0">
                                  <button
                                    className="text-foreground hover:underline"
                                    onClick={() => navigateTo(e.source)}
                                  >
                                    {e.source}
                                  </button>
                                  {" → "}
                                  <span className="text-muted-foreground italic">{e.predicate}</span>
                                  <div className="flex items-center gap-1.5 mt-1">
                                    <span
                                      className="px-1.5 py-px rounded text-[9px]"
                                      style={{
                                        backgroundColor: e.proposed_by === "patient" ? "#0ea5a018" : "#8b5cf618",
                                        color: e.proposed_by === "patient" ? "#0ea5a0" : "#8b5cf6",
                                      }}
                                    >
                                      {e.proposed_by}
                                    </span>
                                    <span
                                      className="px-1.5 py-px rounded text-[9px]"
                                      style={{
                                        backgroundColor: getAcceptanceColor(e.patient_acceptance) + "20",
                                        color: getAcceptanceColor(e.patient_acceptance),
                                      }}
                                    >
                                      {e.patient_acceptance}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-[11px] text-muted-foreground italic">No incoming relations</p>
                      )}
                    </div>
                  </div>
                )}

                {/* Edge Sidebar */}
                {selectedEdge && (
                  <div>
                    {/* Header */}
                    <div className="px-4 py-4 border-b border-border/40" style={{ borderLeftColor: accentColor, borderLeftWidth: 3 }}>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Relationship</span>
                        <button
                          onClick={() => setSelectedEdge(null)}
                          className="p-1 rounded-lg hover:bg-muted/50 transition-colors"
                        >
                          <X className="w-3.5 h-3.5 text-muted-foreground" />
                        </button>
                      </div>
                      <div className="text-sm text-foreground mb-1" style={{ color: accentColor }}>
                        {selectedEdge.predicate}
                      </div>
                    </div>

                    {/* Source Node */}
                    <div className="px-4 py-3 border-b border-border/40">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Source</p>
                      <button
                        className="flex items-center gap-2 hover:bg-muted/40 rounded-lg px-2 py-1.5 -mx-2 transition-colors w-full text-left"
                        onClick={() => selectedEdgeSourceNode && navigateTo(selectedEdgeSourceNode.id)}
                      >
                        {selectedEdgeSourceNode && (
                          <span
                            className="w-3 h-3 rounded-full flex-shrink-0"
                            style={{ backgroundColor: getColor(selectedEdgeSourceNode.label).fill }}
                          />
                        )}
                        <span className="text-sm text-foreground">{selectedEdge.source}</span>
                        <ChevronRight className="w-3 h-3 text-muted-foreground ml-auto" />
                      </button>
                    </div>

                    {/* Target Node */}
                    <div className="px-4 py-3 border-b border-border/40">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Target</p>
                      <button
                        className="flex items-center gap-2 hover:bg-muted/40 rounded-lg px-2 py-1.5 -mx-2 transition-colors w-full text-left"
                        onClick={() => selectedEdgeTargetNode && navigateTo(selectedEdgeTargetNode.id)}
                      >
                        {selectedEdgeTargetNode && (
                          <span
                            className="w-3 h-3 rounded-full flex-shrink-0"
                            style={{ backgroundColor: getColor(selectedEdgeTargetNode.label).fill }}
                          />
                        )}
                        <span className="text-sm text-foreground">{selectedEdge.target}</span>
                        <ChevronRight className="w-3 h-3 text-muted-foreground ml-auto" />
                      </button>
                    </div>

                    {/* Metadata */}
                    <div className="px-4 py-3">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-3">Details</p>
                      <div className="space-y-3">
                        <div>
                          <p className="text-[10px] text-muted-foreground mb-1">Proposed By</p>
                          <span
                            className="px-2 py-0.5 rounded text-[11px]"
                            style={{
                              backgroundColor: selectedEdge.proposed_by === "patient" ? "#0ea5a018" : "#8b5cf618",
                              color: selectedEdge.proposed_by === "patient" ? "#0ea5a0" : "#8b5cf6",
                            }}
                          >
                            {selectedEdge.proposed_by}
                          </span>
                        </div>
                        <div>
                          <p className="text-[10px] text-muted-foreground mb-1">Patient Acceptance</p>
                          <span
                            className="px-2 py-0.5 rounded text-[11px]"
                            style={{
                              backgroundColor: getAcceptanceColor(selectedEdge.patient_acceptance) + "20",
                              color: getAcceptanceColor(selectedEdge.patient_acceptance),
                            }}
                          >
                            {selectedEdge.patient_acceptance}
                          </span>
                        </div>
                        <div>
                          <p className="text-[10px] text-muted-foreground mb-1">Edge Style</p>
                          <span className="text-[11px] text-foreground/70">
                            {selectedEdge.patient_acceptance === "accepted" ? "Solid" :
                             selectedEdge.patient_acceptance === "pending" ? "Dashed" : "Dotted"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Legend ── */}
      <div className="mt-3 flex items-center gap-4 text-[10px] text-muted-foreground flex-wrap">
        <div className="flex items-center gap-1.5">
          <Info className="w-3 h-3" />
          <span>Click nodes/edges for details · Drag to reposition · Scroll to zoom</span>
        </div>
        <div className="flex items-center gap-3 ml-auto flex-wrap">
          <div className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-[#0ea5a0] inline-block rounded" />
            <span>Patient</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-[#8b5cf6] inline-block rounded" />
            <span>Practitioner</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <span>Accepted</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span>Pending</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            <span>Rejected</span>
          </div>
        </div>
      </div>

      {/* ── Ask AI Section ── */}
      <div className="mt-5">
        <button
          onClick={() => setChatOpen(!chatOpen)}
          className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border transition-all duration-200 ${
            chatOpen
              ? "border-primary/40 bg-primary/5 shadow-[0_0_0_2px_rgba(14,165,160,0.08)]"
              : "border-border/40 bg-card hover:border-primary/20 hover:bg-card/80"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-primary" />
            </div>
            <div className="text-left">
              <p className="text-sm text-foreground">Ask AI about this graph</p>
              <p className="text-[11px] text-muted-foreground">
                Powered by Graph RAG · Analyze {patientName}'s knowledge graph
              </p>
            </div>
          </div>
          <motion.div
            animate={{ rotate: chatOpen ? 90 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </motion.div>
        </button>

        <AnimatePresence>
          {chatOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="mt-2 rounded-xl border border-border/40 bg-card overflow-hidden">
                {/* Chat messages */}
                <div className="h-64 overflow-y-auto p-4 space-y-3">
                  {chatMessages.length === 0 && !isAiTyping && (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                      <div className="w-12 h-12 rounded-2xl bg-primary/8 flex items-center justify-center mb-3">
                        <MessageSquare className="w-5 h-5 text-primary/60" />
                      </div>
                      <p className="text-sm text-muted-foreground mb-1">
                        Ask about {patientName}'s graph
                      </p>
                      <p className="text-[11px] text-muted-foreground/60 max-w-xs">
                        Try "Summarize the graph", "What strategies are documented?", or "Show pending relationships"
                      </p>
                      {/* Quick prompts */}
                      <div className="flex flex-wrap gap-1.5 mt-4 justify-center">
                        {["Summarize the graph", "What are the symptoms?", "Show pending relationships"].map(prompt => (
                          <button
                            key={prompt}
                            onClick={() => {
                              setChatInput(prompt);
                            }}
                            className="px-2.5 py-1 text-[11px] bg-muted/50 hover:bg-muted text-muted-foreground rounded-lg transition-colors"
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      {msg.role === "assistant" && (
                        <div className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Bot className="w-3.5 h-3.5 text-primary" />
                        </div>
                      )}
                      <div
                        className={`max-w-[80%] rounded-xl px-3 py-2 ${
                          msg.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted/60 text-foreground"
                        }`}
                      >
                        <p className="text-xs leading-relaxed whitespace-pre-line">{msg.content}</p>
                        <p className={`text-[9px] mt-1 ${
                          msg.role === "user" ? "text-primary-foreground/60" : "text-muted-foreground/60"
                        }`}>
                          {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </p>
                      </div>
                      {msg.role === "user" && (
                        <div className="w-6 h-6 rounded-lg bg-foreground/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <User className="w-3.5 h-3.5 text-foreground/60" />
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Typing indicator */}
                  {isAiTyping && (
                    <div className="flex gap-2.5">
                      <div className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div className="bg-muted/60 rounded-xl px-3 py-2.5 flex items-center gap-1.5">
                        <Loader2 className="w-3 h-3 text-primary animate-spin" />
                        <span className="text-[11px] text-muted-foreground">Thinking…</span>
                      </div>
                    </div>
                  )}

                  <div ref={chatEndRef} />
                </div>

                {/* Input area */}
                <div className="border-t border-border/40 px-3 py-2.5 flex items-center gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    placeholder={`Ask about ${patientName}'s graph…`}
                    className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground/50 outline-none"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={!chatInput.trim() || isAiTyping}
                    className={`p-1.5 rounded-lg transition-all ${
                      chatInput.trim() && !isAiTyping
                        ? "bg-primary text-primary-foreground hover:bg-primary/90"
                        : "bg-muted text-muted-foreground cursor-not-allowed"
                    }`}
                  >
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="px-3 pb-2 flex items-center justify-center gap-1.5">
                  <span className="text-[9px] text-muted-foreground/40">
                    Powered by Graph RAG · {GRAPH_RAG_API_BASE}
                  </span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
