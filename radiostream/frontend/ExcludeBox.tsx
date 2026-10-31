import { X } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { Exclude } from "./api"
import { BOX, BTN, INPUT } from "./ui"

type Rules = Exclude["rules"]
interface Props { ex: Exclude; genres: string[]; busy: boolean; onSave: (rules: Rules, allowLong: boolean) => void }

/** Sender-Einstellung „Ausgeschlossen von Alles“ (nur Admins): Genres, Wortteile, Ordner – mit Ordner-Vorschlägen. */
export function ExcludeBox({ ex, genres, busy, onSave }: Props) {
  const { t } = useTranslation("radiostream")
  const [r, setR] = useState<Rules>(ex.rules)
  const [long, setLong] = useState(ex.allow_long)
  const [part, setPart] = useState("")
  const toggle = (k: keyof Rules, v: string) => setR({ ...r, [k]: r[k].includes(v) ? r[k].filter((x) => x !== v) : [...r[k], v] })
  const chips = (k: keyof Rules) => <div className="flex flex-wrap gap-1">{r[k].map((x) => (
    <span key={x} className="inline-flex items-center gap-1 rounded bg-[rgb(var(--hh-s-hebung,27_37_54))] px-2 py-0.5 text-xs text-[#e8eef8]">{x}
      <button type="button" aria-label={`remove ${x}`} onClick={() => toggle(k, x)}><X size={12} /></button></span>))}</div>
  return (
    <section className={BOX} data-radiostream-exclude>
      <h3 className="text-sm font-semibold text-[#e8eef8]">{t("exclude.heading")}</h3>
      <p className="text-xs text-[#9aa7bc]">{t("exclude.hint")}</p>
      <div className="space-y-1"><span className="text-sm text-[#c8d2df]">{t("exclude.genres")}</span>{chips("genres")}
        <select className={INPUT} value="" aria-label={t("exclude.genres")} onChange={(e) => e.target.value && toggle("genres", e.target.value)}>
          <option value="">{t("mix.add")} …</option>{genres.filter((g) => !r.genres.includes(g)).map((g) => <option key={g} value={g}>{g}</option>)}</select></div>
      <div className="space-y-1"><span className="text-sm text-[#c8d2df]">{t("exclude.parts")}</span>{chips("genre_parts")}
        <div className="flex gap-2"><input className={INPUT} value={part} maxLength={60} aria-label={t("exclude.parts")} onChange={(e) => setPart(e.target.value)} />
          <button type="button" className={BTN} disabled={!part.trim()} onClick={() => { toggle("genre_parts", part.trim().toLowerCase()); setPart("") }}>{t("mix.add")}</button></div></div>
      <div className="space-y-1"><span className="text-sm text-[#c8d2df]">{t("exclude.folders")}</span>{chips("folders")}
        {ex.suggestions.length > 0 && <div className="space-y-1"><p className="text-xs text-[#9aa7bc]">{t("exclude.suggestions")}</p>
          {ex.suggestions.map((s) => (
            <label key={s.folder} className="flex items-center gap-2 text-sm text-[#c8d2df]">
              <input type="checkbox" checked={r.folders.includes(s.folder)} onChange={() => toggle("folders", s.folder)} />
              <span className="break-words">{t("exclude.suggestion", { folder: s.folder, count: s.count })}</span></label>))}</div>}</div>
      <label className="flex items-center gap-2 text-sm text-[#c8d2df]"><input type="checkbox" checked={long} onChange={(e) => setLong(e.target.checked)} />{t("exclude.allow_long")}</label>
      <button type="button" className={BTN} disabled={busy} onClick={() => onSave(r, long)}>{t("exclude.save")}</button>
    </section>
  )
}
