import { useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import { AgentModelPicker } from "@/features/agents/_AgentModelPicker"
import { modelState } from "./caseFormat"
import type { ModelCatalog } from "./useModelCatalog"

/** Modell des Rechts-Agenten im Aufnahmeformular. Standard ist vorausgewählt. Fehlt er im Katalog, ist die Auswahl offen,
 * und ein Hinweis erklärt warum (Fund hydratest 20.10.: sonst 400 ohne Ausweg). */
export function CaseModel({ catalog, value, onChange, error }: {
  catalog: ModelCatalog | null; value: string; onChange: (m: string) => void; error?: string
}) {
  const st = modelState(catalog, value)
  const [open, setOpen] = useState(false)
  const show = open || st.mustChoose
  return (
    <div className="space-y-1 text-xs">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-[#d7deea]">
          Modell des Rechts-Agenten{st.mustChoose ? " *" : ""}:{" "}
          <span className="font-mono font-normal text-[#e8eef8]">{st.effective || (catalog ? "– bitte wählen –" : "Standard")}</span>
        </span>
        {!st.mustChoose && catalog && (
          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={show}
            className="inline-flex items-center gap-0.5 text-[#69d7ff]">
            ändern{show ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        )}
      </div>
      {st.warning && <p className="text-amber-200/90" role="status">{st.warning}</p>}
      {show && catalog && (
        <div className="space-y-2 rounded-[4px] border border-[#2a364b] p-2">
          {value && !st.mustChoose && catalog.selected && (
            <button type="button" onClick={() => onChange("")} className="text-[#69d7ff]">zurück zum Standard ({catalog.selected})</button>
          )}
          <AgentModelPicker value={value} catalog={catalog.models} onChange={onChange} />
        </div>
      )}
      {error && <span className="text-[11px] text-rose-300">{error}</span>}
    </div>
  )
}
