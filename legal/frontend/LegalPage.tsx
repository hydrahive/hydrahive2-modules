import { useState } from "react"
import { Scale } from "lucide-react"
import { CaseFile } from "./CaseFile"
import { CaseList } from "./CaseList"
import { LawSearch } from "./LawSearch"

type Tab = "cases" | "laws"

/** Menüpunkt „Recht“: Reiter Fälle (L2) und Gesetze (L1). Briefe folgen (legal/SPEC-LEGAL.md L3). */
export function LegalPage() {
  const [tab, setTab] = useState<Tab>("cases")
  const [openCase, setOpenCase] = useState<string | null>(null)
  const tabClass = (t: Tab) => (tab === t ? "border-b-2 border-[#69d7ff] px-2 pb-1 font-semibold text-[#e8eef8]" : "px-2 pb-1 text-[#8d9ab0] hover:text-[#d7deea]")
  return (
    <div className="flex h-full min-h-0 flex-col gap-[10px] p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="inline-flex items-center gap-2 text-xl font-bold text-[#e8eef8]"><Scale size={20} />Recht</h1>
        <p className="max-w-xl text-[11px] leading-4 text-amber-200/80">
          Keine Rechtsberatung. Bei Fristen, Klagen und Unsicherheit: Anwalt oder Beratungsstelle.
        </p>
      </header>
      <nav className="flex gap-2 border-b border-[#2a364b] text-sm">
        <button type="button" className={tabClass("cases")} onClick={() => setTab("cases")}>Fälle</button>
        <button type="button" className={tabClass("laws")} onClick={() => setTab("laws")}>Gesetze</button>
      </nav>
      <div className="flex min-h-0 flex-1 flex-col">
        {tab === "laws" && <LawSearch />}
        {tab === "cases" && (openCase
          ? <CaseFile pid={openCase} onBack={() => setOpenCase(null)} />
          : <CaseList onOpen={setOpenCase} />)}
      </div>
    </div>
  )
}
