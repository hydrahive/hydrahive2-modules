import { ResearchSynapse } from "./ResearchSynapse"
import type { Run } from "./api"

const MAX_ROUNDS = 8

function fmt(sec: number): string {
  const s = Math.max(0, Math.floor(sec))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`
}

function phaseLabel(run: Run): string {
  if (run.status === "queued") return "In Warteschlange …"
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
    <div className="dro rounded-2xl border border-white/10 bg-zinc-900/40 p-5">
      <style>{`
        @property --dro-a{syntax:'<angle>';initial-value:0deg;inherits:false}
        @keyframes dro-spin{to{--dro-a:360deg}}
        .dro{position:relative}
        .dro::after{content:'';position:absolute;inset:0;border-radius:1rem;padding:1.5px;
          background:conic-gradient(from var(--dro-a,0deg),transparent 0 295deg,
            color-mix(in srgb,var(--accent,#b8543a) 55%,transparent) 332deg,
            var(--accent,#b8543a) 350deg,transparent 360deg);
          -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
          -webkit-mask-composite:xor;mask-composite:exclude;
          animation:dro-spin 4.5s linear infinite;pointer-events:none}
        @media (prefers-reduced-motion:reduce){.dro::after{animation:none;opacity:.4}}
      `}</style>

      <h1 className="text-lg font-semibold text-zinc-100 mb-4">{run.question}</h1>

      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-zinc-300 truncate">{phaseLabel(run)}</span>
        <span className="font-mono text-xs text-zinc-500">{fmt(p.elapsed_s ?? 0)}</span>
      </div>

      <ResearchSynapse
        round={p.round ?? 0}
        totalSources={p.total_sources ?? 0}
        phase={run.status === "queued" ? "" : p.phase ?? ""}
        query={run.question}
      />

      <div className="mt-3 h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div className="h-full transition-all duration-700" style={{ width: `${pct}%`, background: "var(--accent, #b8543a)" }} />
      </div>

      <div className="mt-3 flex gap-5 font-mono text-[0.7rem] uppercase tracking-wider text-zinc-500">
        <span>Runde <b className="text-zinc-300">{p.round ?? 0}</b></span>
        <span><b className="text-zinc-300">{p.total_sources ?? 0}</b> Quellen</span>
        <span><b className="text-zinc-300">{p.total_findings ?? 0}</b> Funde</span>
      </div>
    </div>
  )
}
