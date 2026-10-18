import { useState } from "react"
import { AudioLines, Film, Image, Loader2, Music, Search, User } from "lucide-react"
import { useTranslation } from "react-i18next"
import { MEDIA_MIME } from "./cutDnd"
import { fileUrl } from "@/shared/files"
import type { LibraryItem, MediaKind } from "./api"
import { FILTERS, grouped, visible, type Filter } from "./libraryView"

const ICON: Record<MediaKind, typeof Film> = { video: Film, image: Image, audio: AudioLines, music: Music, element: User }

interface Props {
  items: LibraryItem[]
  loading: boolean
  error: string | null
  truncated: boolean
  selected: string | null
  onSelect: (id: string) => void
}

/** Bibliothek: echte Medien des Projekts – eine Liste für alles, Filter, Suche, Ordner nach Herkunft. */
export function LibraryPanel({ items, loading, error, truncated, selected, onSelect }: Props) {
  const { t } = useTranslation("studio")
  const [filter, setFilter] = useState<Filter>("all")
  const [query, setQuery] = useState("")
  const groups = grouped(visible(items, filter, query))
  return (
    <section className="flex h-full min-h-0 flex-col" data-studio-panel="library">
      <div className="flex items-center justify-between px-3 pt-2">
        <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("library")}</h2>
        <span className="text-[10px] text-[#68758a]" data-library-count={items.length}>{t("library_count", { count: items.length })}</span>
      </div>
      <div className="flex flex-wrap gap-1 px-3 pt-2">
        {FILTERS.map((f) => (
          <button key={f} type="button" data-library-filter={f} aria-pressed={f === filter} onClick={() => setFilter(f)}
            className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${f === filter ? "bg-[#69d7ff] text-[#08111c]" : "bg-[#111827] text-[#8d9ab0]"}`}>
            {t(`kind.${f}`)}
          </button>
        ))}
      </div>
      <label className="mx-3 mt-2 flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-1">
        <Search size={12} className="text-[#68758a]" />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("search")}
          className="w-full bg-transparent text-xs text-[#e8eef8] outline-none placeholder:text-[#68758a]" />
      </label>
      <div className="mt-2 min-h-0 flex-1 space-y-3 overflow-y-auto px-2 pb-3">
        {loading && <p className="flex items-center gap-1.5 px-2 text-xs text-[#68758a]"><Loader2 size={12} className="animate-spin" /> {t("loading")}</p>}
        {error && <p className="px-2 text-xs text-[#ff6b8a]" data-library-error>{error}</p>}
        {groups.map((g) => (
          <div key={g.group}>
            <p className="px-1 pb-1 text-[10px] font-bold uppercase tracking-wide text-[#68758a]">{t(`origin.${g.group}`)}</p>
            <ul className="space-y-0.5">{g.items.map((m) => <Item key={m.id} m={m} active={m.id === selected} onSelect={onSelect} />)}</ul>
          </div>
        ))}
        {!loading && !error && !groups.length && (
          <p className="px-2 text-xs leading-relaxed text-[#68758a]" data-library-empty>{items.length ? t("library_empty") : t("library_none")}</p>
        )}
        {truncated && <p className="px-2 text-[10px] text-[#ffb86b]">{t("library_truncated")}</p>}
      </div>
    </section>
  )
}

function Thumb({ m }: { m: LibraryItem }) {
  const Icon = ICON[m.kind]
  const src = m.kind === "image" ? m.abs : m.thumb_abs
  return (
    <span className="relative grid h-8 w-12 shrink-0 place-items-center overflow-hidden rounded-[3px] bg-[#1c2940]">
      {src ? <img src={fileUrl(src)} alt="" loading="lazy" className="h-full w-full object-cover" />
        : m.kind === "video" ? <video src={`${fileUrl(m.abs)}#t=0.5`} preload="metadata" muted className="h-full w-full object-cover" />
          : <Icon size={13} className="text-[#8d9ab0]" />}
    </span>
  )
}

function Item({ m, active, onSelect }: { m: LibraryItem; active: boolean; onSelect: (id: string) => void }) {
  const { t } = useTranslation("studio")
  return (
    <li>
      <button type="button" data-library-item={m.id} data-library-kind={m.kind} onClick={() => onSelect(m.id)} title={m.prompt ?? m.name}
        draggable={m.kind !== "element"}
        onDragStart={(e) => { e.dataTransfer.setData(MEDIA_MIME, m.id); e.dataTransfer.effectAllowed = "copy" }}
        className={`flex w-full items-center gap-2 rounded-[4px] px-1.5 py-1 text-left ${active ? "bg-[#1c2940]" : "hover:bg-[#111827]"}`}>
        <Thumb m={m} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs text-[#e8eef8]">{m.name}</span>
          <span className="block truncate text-[10px] text-[#68758a]">
            {t(`kind.${m.kind}`)}{m.duration ? ` · ${m.duration} s` : ""} · {t(`source.${m.source}`)}
          </span>
        </span>
      </button>
    </li>
  )
}
