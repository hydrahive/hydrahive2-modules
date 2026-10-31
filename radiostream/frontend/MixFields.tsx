import { X } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { BTN, INPUT } from "./ui"

interface Base { label: string; values: string[]; readOnly: boolean; exclude?: boolean; onChange: (v: string[]) => void }

/** Gewählte Werte als kleine Marken mit Entfernen-Knopf. */
export function Chips({ values, readOnly, exclude, onChange }: Omit<Base, "label">) {
  return (
    <div className="flex flex-wrap gap-1">
      {values.map((x) => (
        <span key={x} className="inline-flex items-center gap-1 rounded bg-[rgb(var(--hh-s-hebung,27_37_54))] px-2 py-0.5 text-xs text-[#e8eef8]">
          {exclude ? "− " : ""}{x}
          {!readOnly && <button type="button" aria-label={`remove ${x}`} onClick={() => onChange(values.filter((y) => y !== x))}><X size={12} /></button>}
        </span>))}
    </div>)
}

/** Auswahl aus einer festen Liste (Genres). */
export function PickField({ label, values, readOnly, exclude, onChange, options }: Base & { options: string[] }) {
  const { t } = useTranslation("radiostream")
  return (
    <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t(label)}</span>
      <Chips values={values} readOnly={readOnly} exclude={exclude} onChange={onChange} />
      {!readOnly && <select className={INPUT} value="" aria-label={t(label)} onChange={(e) => e.target.value && onChange([...values, e.target.value])}>
        <option value="">{t("mix.add")} …</option>
        {options.filter((o) => !values.includes(o)).map((o) => <option key={o} value={o}>{o}</option>)}
      </select>}
    </label>)
}

/** Freie Eingabe (Interpreten) bzw. mit Vorschlagsliste (Ordner, sehr viele). */
export function TypedField({ label, values, readOnly, exclude, onChange, options, listId }: Base & { options?: string[]; listId?: string }) {
  const { t } = useTranslation("radiostream")
  const [v, setV] = useState("")
  const add = () => { const x = v.trim(); if (x && !values.includes(x)) onChange([...values, x]); setV("") }
  return (
    <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t(label)}</span>
      <Chips values={values} readOnly={readOnly} exclude={exclude} onChange={onChange} />
      {!readOnly && <div className="flex gap-2">
        <input className={INPUT} value={v} maxLength={200} aria-label={t(label)} list={options ? listId : undefined}
          placeholder={options ? t("mix.folder_placeholder") : t("mix.artist_placeholder")}
          onChange={(e) => setV(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add() } }} />
        {options && <datalist id={listId}>{options.map((o) => <option key={o} value={o} />)}</datalist>}
        <button type="button" className={BTN} onClick={add}>{t("mix.add")}</button></div>}
    </label>)
}
