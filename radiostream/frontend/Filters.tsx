import { Search } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Filter } from "./logic"

const DECADES = ["1950", "1960", "1970", "1980", "1990", "2000", "2010", "2020"]

/** Suchfeld + Genre, Jahrzehnt, Format, „Nicht mehr da“. */
export function Filters({ f, genres, onChange }: { f: Filter; genres: string[]; onChange: (f: Filter) => void }) {
  const { t } = useTranslation("radiostream")
  const sel = "rounded border border-white/10 bg-zinc-900 px-2 py-1.5 text-sm text-zinc-200"
  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="flex min-w-[220px] flex-1 items-center gap-2 rounded border border-white/10 bg-white/[3%] px-3 py-1.5">
        <Search size={14} className="text-zinc-500" />
        <input value={f.q} onChange={(e) => onChange({ ...f, q: e.target.value })} placeholder={t("search_placeholder")}
          aria-label={t("search_placeholder")} className="w-full bg-transparent text-sm text-zinc-100 outline-none" />
      </label>
      <select value={f.genre} onChange={(e) => onChange({ ...f, genre: e.target.value })} aria-label={t("filter.all_genres")} className={sel}>
        <option value="">{t("filter.all_genres")}</option>
        {genres.map((g) => <option key={g} value={g}>{g}</option>)}
      </select>
      <select value={f.decade} onChange={(e) => onChange({ ...f, decade: e.target.value })} aria-label={t("filter.all_decades")} className={sel}>
        <option value="">{t("filter.all_decades")}</option>
        {DECADES.map((d) => <option key={d} value={d}>{t("decade", { decade: d })}</option>)}
      </select>
      <select value={f.format} onChange={(e) => onChange({ ...f, format: e.target.value })} aria-label={t("filter.all_formats")} className={sel}>
        <option value="">{t("filter.all_formats")}</option>
        <option value="mp3">MP3</option>
        <option value="flac">FLAC</option>
      </select>
      <label className="flex items-center gap-1.5 text-sm text-zinc-300">
        <input type="checkbox" checked={f.missing} onChange={(e) => onChange({ ...f, missing: e.target.checked })} />
        {t("filter.missing")}
      </label>
    </div>
  )
}
