import { Search, SlidersHorizontal } from "lucide-react"
import { useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"
import { MEDIA_TYPES } from "./format"
import type { MediaType, SearchFilters } from "./types"

interface Props {
  loading: boolean
  disabled: boolean
  onSearch: (filters: SearchFilters) => void
}

const inputClass = "w-full rounded-[4px] border border-[#30405a] bg-[#0c121d] px-3 py-2 text-sm text-[#e8eef8] outline-none placeholder:text-[#5f6d82] focus:border-cyan-400/70"
const optionalNumber = (value: string) => value ? Number(value) : undefined

export function SearchPanel({ loading, disabled, onSearch }: Props) {
  const { t } = useTranslation("mediacenter")
  const [mediaType, setMediaType] = useState<MediaType>("movie")
  const [query, setQuery] = useState("")
  const [advanced, setAdvanced] = useState(false)
  const [year, setYear] = useState("")
  const [season, setSeason] = useState("")
  const [episode, setEpisode] = useState("")
  const [author, setAuthor] = useState("")
  const [artist, setArtist] = useState("")
  const [album, setAlbum] = useState("")
  const [maxAge, setMaxAge] = useState("")
  const [minSize, setMinSize] = useState("")
  const [maxSize, setMaxSize] = useState("")

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (query.trim().length < 2) return
    const filters: SearchFilters = {
      query: query.trim(), media_type: mediaType, limit: 50,
      year: optionalNumber(year), max_age_days: optionalNumber(maxAge),
      min_size_mb: optionalNumber(minSize), max_size_mb: optionalNumber(maxSize),
    }
    if (mediaType === "tv") Object.assign(filters, { season: optionalNumber(season), episode: episode || undefined })
    if (mediaType === "book") filters.author = author || undefined
    if (mediaType === "music") Object.assign(filters, { artist: artist || undefined, album: album || undefined })
    onSearch(filters)
  }

  return <section className="rounded-[6px] border border-[#28354a] bg-[#101724] p-4">
    <div className="mb-4 flex gap-1 overflow-x-auto" role="tablist" aria-label={t("search.mediaTypes")}>
      {MEDIA_TYPES.map((item) => <button key={item.id} type="button" role="tab"
        aria-selected={mediaType === item.id} onClick={() => setMediaType(item.id)}
        className={`shrink-0 rounded-[4px] px-3 py-2 text-xs font-bold transition ${mediaType === item.id ? "bg-cyan-400/15 text-cyan-200 ring-1 ring-cyan-400/40" : "text-[#8d9ab0] hover:bg-white/[5%] hover:text-[#d4deeb]"}`}>
        {t(`media.${item.id}`)}
      </button>)}
    </div>
    <form onSubmit={submit} className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <label className="sr-only" htmlFor="mediacenter-query">{t("search.query")}</label>
        <input id="mediacenter-query" className={inputClass} value={query} maxLength={200}
          onChange={(event) => setQuery(event.target.value)} placeholder={t(`search.placeholders.${mediaType}`)} disabled={disabled} />
        <button type="submit" disabled={disabled || loading || query.trim().length < 2}
          className="flex shrink-0 items-center justify-center gap-2 rounded-[4px] bg-cyan-400/20 px-4 py-2 text-sm font-bold text-cyan-100 ring-1 ring-cyan-400/50 transition hover:bg-cyan-400/30 disabled:cursor-not-allowed disabled:opacity-40">
          <Search size={15} />{loading ? t("search.searching") : t("search.submit")}
        </button>
      </div>
      <button type="button" onClick={() => setAdvanced((value) => !value)}
        className="flex items-center gap-2 text-xs font-semibold text-[#8d9ab0] hover:text-[#d4deeb]">
        <SlidersHorizontal size={13} />{t("search.filters")}
      </button>
      {advanced && <div className="grid gap-3 border-t border-[#263247] pt-3 sm:grid-cols-2 lg:grid-cols-4">
        <Field label={t("search.year")} value={year} onChange={setYear} type="number" min="1800" max="2100" />
        {mediaType === "tv" && <><Field label={t("search.season")} value={season} onChange={setSeason} type="number" min="0" max="999" /><Field label={t("search.episode")} value={episode} onChange={setEpisode} /></>}
        {mediaType === "book" && <Field label={t("search.author")} value={author} onChange={setAuthor} />}
        {mediaType === "music" && <><Field label={t("search.artist")} value={artist} onChange={setArtist} /><Field label={t("search.album")} value={album} onChange={setAlbum} /></>}
        <Field label={t("search.maxAge")} value={maxAge} onChange={setMaxAge} type="number" min="1" max="3650" />
        <Field label={t("search.minSize")} value={minSize} onChange={setMinSize} type="number" min="0" />
        <Field label={t("search.maxSize")} value={maxSize} onChange={setMaxSize} type="number" min="0" />
      </div>}
    </form>
  </section>
}

function Field({ label, value, onChange, type = "text", min, max }: { label: string; value: string; onChange: (value: string) => void; type?: string; min?: string; max?: string }) {
  return <label className="text-xs font-semibold text-[#8d9ab0]">{label}<input className={`${inputClass} mt-1`} type={type} min={min} max={max} value={value} onChange={(event) => onChange(event.target.value)} /></label>
}
