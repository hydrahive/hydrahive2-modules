// KI-Modell (Spec 1b §5, Ghostwriter §3.6): dasselbe Auswahlfeld wie im Agent-Editor (Suche, Anbieter,
// „nur gratis“, nach Anbieter gruppiert). Leer = Rückfall: erst `fallback` (z. B. Buchmodell), dann
// HydraHive-Standardmodell für Chat. Kein Modell ist fest eingebaut.
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ChevronDown, ChevronUp } from "lucide-react"
import { AgentModelPicker } from "@/features/agents/_AgentModelPicker"
import { loadChatModels, type Catalog } from "../chatModels"

interface Props {
  value: string
  onChange: (model: string) => void
  compact?: boolean
  /** Beschriftung vor dem Modellnamen (Standard: „Modell:“). */
  label?: string
  /** Wird benutzt, wenn `value` leer ist (z. B. Buchmodell für den Ghostwriter). */
  fallback?: string
}

export function ModelChooser({ value, onChange, compact = false, label: caption, fallback = "" }: Props) {
  const { t } = useTranslation("storyteller")
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [error, setError] = useState("")
  const [open, setOpen] = useState(false)
  useEffect(() => {
    let alive = true
    loadChatModels().then((c) => { if (alive) setCatalog(c) }).catch((e) => { if (alive) setError(e instanceof Error ? e.message : String(e)) })
    return () => { alive = false }
  }, [])

  const inherited = fallback
    ? t("ai_model_inherited", { model: fallback })
    : t("ai_model_standard", { model: catalog?.standard || "…" })
  const label = value || inherited
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 text-xs text-zinc-400">
          {!compact && <span className="mr-1">{caption ?? t("ai_model_label")}</span>}
          <span className="st-model font-mono text-zinc-200" title={label}>{label}</span>
        </div>
        <button onClick={() => setOpen((o) => !o)} aria-expanded={open}
          className="inline-flex shrink-0 items-center gap-0.5 rounded px-2 py-0.5 text-xs text-violet-300 hover:bg-violet-500/10">
          {t("ai_model_change")}{open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>
      </div>
      {open && (
        <div className="space-y-2 rounded-lg border border-white/10 bg-zinc-950/60 p-2">
          <label className="flex items-center gap-2 text-xs text-zinc-300">
            <input type="radio" checked={!value} onChange={() => onChange("")} />
            {fallback ? t("ai_model_use_inherited", { model: fallback }) : t("ai_model_use_standard", { model: catalog?.standard || "…" })}
          </label>
          {error && <p className="text-xs text-red-300">{t("ai_models_failed", { error })}</p>}
          {catalog
            ? <AgentModelPicker value={value} catalog={catalog.models} onChange={onChange} />
            : !error && <p className="text-xs text-zinc-500">…</p>}
        </div>
      )}
    </div>
  )
}
