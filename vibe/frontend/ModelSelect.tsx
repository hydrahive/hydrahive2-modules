import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { INPUT } from "./ui"

/** Auswahl des Sprachmodells. `value` leer = Standardmodell des Systems. Lädt die Liste selbst (einmal je Seite). */
export function ModelSelect({ value, onChange, disabled, label, onUsable }: {
  value: string; onChange: (m: string) => void; disabled?: boolean; label?: string; onUsable?: (ok: boolean) => void
}) {
  const { t } = useTranslation("vibe")
  const [items, setItems] = useState<api.VibeModel[]>([])
  const [def, setDef] = useState("")
  const [defOk, setDefOk] = useState(true)
  useEffect(() => { api.getModels().then((r) => { setItems(r.items); setDef(r.default); setDefOk(r.default_listed) }).catch(() => setItems([])) }, [])
  // Steht das Standardmodell nicht in der Liste der eingerichteten Anbieter, hat der Server dafür vermutlich keinen
  // Zugang: dann nichts vorwählen (sonst bricht der erste Chat mit einer Fehlermeldung ab) und es sagen.
  const unusable = !defOk && !value
  const current = value || (defOk ? def : "")
  const usable = !!current && items.length > 0
  useEffect(() => { onUsable?.(usable) }, [usable, onUsable])
  const known = items.some((m) => m.id === current)
  return (
    <label className="block space-y-1 text-sm text-[#c8d2df]">
      {label && <span>{label}</span>}
      <select className={INPUT} value={current} disabled={disabled || items.length === 0} onChange={(e) => onChange(e.target.value)}>
        {unusable && <option value="">{t("model_pick")}</option>}
        {!known && current && <option value={current}>{current}</option>}
        {items.length === 0 && <option value="">{t("model_none")}</option>}
        {items.map((m) => <option key={m.id} value={m.id}>{m.label} ({m.provider})</option>)}
      </select>
      {!unusable && current.startsWith("openai-codex/") && <span className="block text-xs text-[#9aa7bc]">{t("model_codex_hint")}</span>}
      {unusable && <span className="block text-xs text-amber-200" role="status">{t("model_default_missing", { model: def })}</span>}
    </label>
  )
}
