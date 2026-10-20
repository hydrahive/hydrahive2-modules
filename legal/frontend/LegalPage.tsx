import { Scale } from "lucide-react"
import { LawSearch } from "./LawSearch"

/** Menüpunkt „Recht“. L1: Reiter Gesetze. Fälle, Fristen und Briefe folgen (legal/SPEC-LEGAL.md L2/L3). */
export function LegalPage() {
  return (
    <div className="flex h-full min-h-0 flex-col gap-[10px] p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="inline-flex items-center gap-2 text-xl font-bold text-[#e8eef8]"><Scale size={20} />Recht</h1>
        <p className="max-w-xl text-[11px] leading-4 text-amber-200/80">
          Keine Rechtsberatung. Bei Fristen, Klagen und Unsicherheit: Anwalt oder Beratungsstelle.
        </p>
      </header>
      <nav className="flex gap-2 border-b border-[#2a364b] text-sm">
        <span className="border-b-2 border-[#69d7ff] px-2 pb-1 font-semibold text-[#e8eef8]">Gesetze</span>
        <span className="px-2 pb-1 text-[#68758a]" title="Kommt in der nächsten Etappe">Fälle (bald)</span>
      </nav>
      <div className="min-h-0 flex-1"><LawSearch /></div>
    </div>
  )
}
