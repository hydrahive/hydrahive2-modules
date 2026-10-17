import { useState } from "react"
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { PlanOutline } from "./PlanOutline"
import type { PlanState } from "./usePlan"

/** Planen, links: Reiter „Drehbuch“ (Gliederung) und „Bibliothek“ (die bisherige Medienliste). */
export function PlanSidebar({ p, library }: { p: PlanState; library: React.ReactNode }) {
  const { t } = useTranslation("studio")
  const [tab, setTab] = useState<"outline" | "library">("outline")
  return (
    <section className="flex h-full min-h-0 flex-col" data-studio-panel="library">
      <div className="flex gap-1 border-b border-[#2a364b] px-2 pt-2" role="tablist">
        {(["outline", "library"] as const).map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} data-plan-tab={k} onClick={() => setTab(k)}
            className={`rounded-t-[4px] px-2.5 py-1 text-[11px] font-black uppercase tracking-[0.1em] ${tab === k ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#68758a] hover:text-[#e8eef8]"}`}>
            {t(k === "outline" ? "screenplay" : "library")}
          </button>
        ))}
      </div>
      {tab === "library" ? <div className="min-h-0 flex-1">{library}</div>
        : p.plan ? (
          <PlanOutline plan={p.plan} preview={p.preview} selection={p.selection} onSelect={p.select} onMove={(id, d) => void p.move(id, d)}
            onAddScene={() => void p.addScene()} onAddElement={(k) => void p.addElement(k)} onImport={() => p.setDialog({ kind: "import" })} />
        ) : p.error ? <p className="p-3 text-xs text-[#ff6b8a]" data-plan-error>{p.error}</p>
          : <p className="flex items-center gap-1.5 p-3 text-xs text-[#68758a]"><Loader2 size={12} className="animate-spin" /> {t("loading")}</p>}
    </section>
  )
}
