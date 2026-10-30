import type { RunListItem } from "./api"

export type RunFilter = "all" | "active" | "done"

interface RunListProps {
  runs: RunListItem[]
  activeId: string | null
  filter: RunFilter
  onFilter: (f: RunFilter) => void
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}

const STATUS: Record<string, { icon: string; cls: string }> = {
  queued: { icon: "⏳", cls: "text-amber-400" },
  running: { icon: "⋯", cls: "text-sky-400 animate-pulse" },
  done: { icon: "✓", cls: "text-emerald-400" },
  error: { icon: "✕", cls: "text-rose-400" },
}

function matches(f: RunFilter, status: string): boolean {
  if (f === "active") return status === "queued" || status === "running"
  if (f === "done") return status === "done" || status === "error"
  return true
}

const CHIPS: { key: RunFilter; label: string }[] = [
  { key: "all", label: "Alle" },
  { key: "active", label: "Läuft" },
  { key: "done", label: "Fertig" },
]

export function RunList({ runs, activeId, filter, onFilter, onSelect, onDelete }: RunListProps) {
  const filtered = runs.filter((r) => matches(filter, r.status))
  return (
    <div className="pt-3 border-t border-[rgb(var(--hh-s-rand,42_54_75))]">
      <div className="flex gap-1 mb-2">
        {CHIPS.map((c) => (
          <button
            key={c.key}
            onClick={() => onFilter(c.key)}
            className={`px-2 py-1 rounded-md text-xs ${
              filter === c.key ? "bg-[rgb(var(--hh-s-hebung,27_37_54))] text-[#e8eef8]" : "text-[#9aa7bc] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>
      {filtered.length === 0 && <p className="text-[#9aa7bc] text-sm py-1">Nichts hier</p>}
      <div className="space-y-1">
        {filtered.map((r) => {
          const s = STATUS[r.status] ?? STATUS.queued
          const isActive = activeId === r.id
          return (
            <div
              key={r.id}
              className={`group flex items-center gap-2 px-2.5 py-2 rounded-lg ${
                isActive ? "bg-[rgb(var(--hh-s-hebung,27_37_54))]" : "hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
              }`}
            >
              <span className={`text-xs w-3 text-center ${s.cls}`}>{s.icon}</span>
              <button
                onClick={() => onSelect(r.id)}
                className={`flex-1 text-left text-sm truncate ${isActive ? "text-[#e8eef8]" : "text-[#c8d2df]"}`}
              >
                {r.question || "Ohne Titel"}
              </button>
              <button
                onClick={() => onDelete(r.id)}
                className="opacity-0 group-hover:opacity-100 text-[#9aa7bc] hover:text-rose-400 text-xs px-1"
                title="Löschen"
              >
                ✕
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
