/**
 * Custom-Node-Komponenten für Blueprint. Zwei Familien:
 *  - Layout-Nodes (kind="layout"): neutral/zinc, zeigen wie eine Seite aussehen
 *    soll. Andockpunkte oben/unten (vertikaler Fluss von Layout-Hierarchie).
 *  - Flow-Nodes (kind="flow"): bunt nach Rolle, zeigen Abläufe. Andockpunkte
 *    links/rechts (horizontaler Datenfluss).
 * Beide teilen sich ein Board und sind frei verbindbar (jeder Handle an jeden).
 */
import { Handle, Position, type NodeTypes } from "@xyflow/react"
import { moduleIcon } from "@/shared/module-icon"
import { iconOf, labelOf } from "./palette-data"
import type { BlueprintNodeData } from "./types"

interface NodeProps {
  data: BlueprintNodeData
  selected: boolean
}

const DOT = { width: 9, height: 9 }

// Farbschema je Flow-subtype (Layout ist immer neutral).
const FLOW_COLOR: Record<string, { border: string; bg: string; text: string; dot: string }> = {
  event: { border: "border-amber-500/60", bg: "bg-amber-950/40", text: "text-amber-300", dot: "#f59e0b" },
  action: { border: "border-sky-500/60", bg: "bg-sky-950/40", text: "text-sky-300", dot: "#0ea5e9" },
  datasource: { border: "border-violet-500/60", bg: "bg-violet-950/40", text: "text-violet-300", dot: "#8b5cf6" },
  condition: { border: "border-blue-500/60", bg: "bg-blue-950/40", text: "text-blue-300", dot: "#3b82f6" },
  display: { border: "border-emerald-500/60", bg: "bg-emerald-950/40", text: "text-emerald-300", dot: "#10b981" },
  note: { border: "border-yellow-500/50", bg: "bg-yellow-950/30", text: "text-yellow-200", dot: "#eab308" },
}

function Shell({ data, selected, children, accent }: {
  data: BlueprintNodeData; selected: boolean; children?: React.ReactNode; accent: string
}) {
  const Icon = moduleIcon(iconOf(data.subtype))
  return (
    <div className={`min-w-[150px] max-w-[230px] rounded-xl border-2 px-3 py-2 shadow-lg select-none ${accent} ${
      selected ? "ring-2 ring-white/30" : ""
    }`}>
      <div className="mb-0.5 flex items-center gap-1.5">
        <Icon size={12} />
        <span className="text-[0.5rem] font-bold uppercase tracking-widest opacity-70">
          {labelOf(data.subtype)}
        </span>
      </div>
      <p className="text-sm font-medium leading-tight text-white">{data.label || "—"}</p>
      {data.note && <p className="mt-0.5 text-[11px] leading-snug opacity-60">{data.note}</p>}
      {children}
    </div>
  )
}

// Layout-Node: neutral, Handles oben (Input) + unten (Output) für Hierarchie.
export function LayoutNodeComp({ data, selected }: NodeProps) {
  return (
    <>
      <Handle type="target" position={Position.Top} id="in"
        style={{ ...DOT, background: "#71717a", border: "2px solid #52525b" }} />
      <Shell data={data} selected={selected} accent="border-zinc-600/70 bg-zinc-800/70 text-zinc-200" />
      <Handle type="source" position={Position.Bottom} id="out"
        style={{ ...DOT, background: "#71717a", border: "2px solid #52525b" }} />
    </>
  )
}

// Flow-Node: farbig je Rolle, Handles links (Input) + rechts (Output).
// condition hat zwei Outputs (true/false).
export function FlowNodeComp({ data, selected }: NodeProps) {
  const c = FLOW_COLOR[data.subtype] ?? FLOW_COLOR.action
  const isEvent = data.subtype === "event"
  const isDisplay = data.subtype === "display"
  const isNote = data.subtype === "note"
  const isCondition = data.subtype === "condition"

  return (
    <>
      {!isEvent && !isNote && (
        <Handle type="target" position={Position.Left} id="in"
          style={{ ...DOT, background: c.dot, border: `2px solid ${c.dot}` }} />
      )}
      <Shell data={data} selected={selected} accent={`${c.border} ${c.bg} ${c.text}`}>
        {isCondition && (
          <div className="relative mt-1.5 h-6">
            <Handle type="source" position={Position.Right} id="true"
              style={{ ...DOT, top: "20%", background: "#22c55e", border: "2px solid #16a34a" }} />
            <span className="absolute right-[-26px] top-[-2px] text-[9px] font-semibold text-green-400">ja</span>
            <Handle type="source" position={Position.Right} id="false"
              style={{ ...DOT, top: "80%", background: "#ef4444", border: "2px solid #dc2626" }} />
            <span className="absolute right-[-30px] top-[14px] text-[9px] font-semibold text-red-400">nein</span>
          </div>
        )}
      </Shell>
      {!isDisplay && !isNote && !isCondition && (
        <Handle type="source" position={Position.Right} id="out"
          style={{ ...DOT, background: c.dot, border: `2px solid ${c.dot}` }} />
      )}
    </>
  )
}

export const NODE_TYPES: NodeTypes = {
  layoutNode: LayoutNodeComp as never,
  flowNode: FlowNodeComp as never,
}

// subtype → ReactFlow node-type
export function nodeTypeFor(kind: "layout" | "flow"): string {
  return kind === "layout" ? "layoutNode" : "flowNode"
}
