import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { INPUT } from "./ui"

/** Auswahl des Sprachmodells. `value` leer = Standardmodell des Systems. Lädt die Liste selbst (einmal je Seite). */
export function ModelSelect({ value, onChange, disabled, label }: { value: string; onChange: (m: string) => void; disabled?: boolean; label?: string }) {
  const { t } = useTranslation("vibe")
  const [items, setItems] = useState<api.VibeModel[]>([])
  const [def, setDef] = useState("")
  useEffect(() => { api.getModels().then((r) => { setItems(r.items); setDef(r.default) }).catch(() => setItems([])) }, [])
  const current = value || def
  const known = items.some((m) => m.id === current)
  return (
    <label className="block space-y-1 text-sm text-[#c8d2df]">
      {label && <span>{label}</span>}
      <select className={INPUT} value={current} disabled={disabled || items.length === 0} onChange={(e) => onChange(e.target.value)}>
        {!known && current && <option value={current}>{current}</option>}
        {items.length === 0 && <option value="">{t("model_none")}</option>}
        {items.map((m) => <option key={m.id} value={m.id}>{m.label} ({m.provider})</option>)}
      </select>
    </label>
  )
}
