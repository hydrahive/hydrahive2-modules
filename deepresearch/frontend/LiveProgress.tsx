import { ResearchSynapse } from "./ResearchSynapse"
import type { Run } from "./api"

const MAX_ROUNDS = 6

function fmt(sec: number): string {
  const s = Math.max(0, Math.floor(sec))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`
}

function phaseLabel(run: Run): string {
  const p = run.progress
  switch (p.phase) {
    case "planning":
      return "Plane Recherche-Strategie …"
    case "searching":
      return `Suche · ${p.queries ?? 0} Queries`
    case "reading":
      return `Liest: ${p.current?.title ?? "…"}`
    case "analyzing":
      return `Analysiere · ${p.total_findings ?? 0} Funde`
    case "writing":
      return "Schreibe Bericht …"
    case "done":
      return "Fertig"
    default:
      return "Startet …"
  }
}

export function LiveProgress({ run }: { run: Run }) {
  const p = run.progress
  const pct = Math.min(100, Math.round(((p.round ?? 0) / MAX_ROUNDS) * 100))

  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-900/40 p-5">
      <h1 className="text-lg font-semibold text-zinc-100 mb-4">{run.question}</h1>

      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-zinc-300 truncate">{phaseLabel(run)}</span>
        <span className="font-mono text-xs text-zinc-500">{fmt(p.elapsed_s ?? 0)}</span>
      </div>

      <ResearchSynapse round={p.round ?? 1} totalSources={p.total_sources ?? 0} phase={p.phase ?? ""} />

      <div className="mt-3 h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full transition-all duration-700"
          style={{ width: `${pct}%`, background: "var(--accent, #e0795e)" }}
        />
      </div>

      <div className="mt-3 flex gap-5 font-mono text-[0.7rem] uppercase tracking-wider text-zinc-500">
        <span>
          Runde <b className="text-zinc-300">{p.round ?? 0}</b>
        </span>
        <span>
          <b className="text-zinc-300">{p.total_sources ?? 0}</b> Quellen
        </span>
        <span>
          <b className="text-zinc-300">{p.total_findings ?? 0}</b> Funde
        </span>
      </div>
    </div>
  )
}
