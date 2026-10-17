import { useState } from "react"
import { AudioLines, Film, Image, Music, Search, Upload, User } from "lucide-react"
import { useTranslation } from "react-i18next"
import { DEMO_MEDIA, type DemoMedia, type MediaKind, type Origin } from "./demoData"

const FILTERS: (MediaKind | "all")[] = ["all", "video", "image", "audio", "music", "element"]
const ICON: Record<MediaKind, typeof Film> = { video: Film, image: Image, audio: AudioLines, music: Music, element: User }
const GROUPS: Origin[] = ["ai", "upload", "legacy"]

/** Bibliothek: eine Liste für alles, Filter nach Art, Suche, Ordner nach Herkunft. */
export function LibraryPanel({ selected, onSelect }: { selected: string | null; onSelect: (id: string) => void }) {
  const { t } = useTranslation("studio")
  const [filter, setFilter] = useState<MediaKind | "all">("all")
  const [query, setQuery] = useState("")
  const items = DEMO_MEDIA.filter((m) => (filter === "all" || m.kind === filter)
    && m.name.toLowerCase().includes(query.trim().toLowerCase()))
  return (
    <section className="flex h-full min-h-0 flex-col" data-studio-panel="library">
      <div className="flex items-center justify-between px-3 pt-2">
        <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("library")}</h2>
        <button type="button" className="rounded-[4px] p-1 text-[#8d9ab0] hover:text-[#e8eef8]" title={t("upload")}><Upload size={13} /></button>
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
        {GROUPS.map((g) => {
          const list = items.filter((m) => m.origin === g)
          if (!list.length) return null
          return (
            <div key={g}>
              <p className="px-1 pb-1 text-[10px] font-bold uppercase tracking-wide text-[#3f4b60]">{t(`origin.${g}`)}</p>
              <ul className="space-y-0.5">{list.map((m) => <Item key={m.id} m={m} active={m.id === selected} onSelect={onSelect} />)}</ul>
            </div>
          )
        })}
        {!items.length && <p className="px-2 text-xs text-[#68758a]">{t("library_empty")}</p>}
      </div>
    </section>
  )
}

function Item({ m, active, onSelect }: { m: DemoMedia; active: boolean; onSelect: (id: string) => void }) {
  const Icon = ICON[m.kind]
  return (
    <li>
      <button type="button" draggable data-library-item={m.id} onClick={() => onSelect(m.id)}
        className={`flex w-full items-center gap-2 rounded-[4px] px-1.5 py-1 text-left ${active ? "bg-[#1c2940]" : "hover:bg-[#111827]"}`}>
        <span className="grid h-8 w-12 shrink-0 place-items-center rounded-[3px]"
          style={{ background: `linear-gradient(135deg, hsl(${m.hue} 45% 32%), hsl(${m.hue + 30} 50% 18%))` }}>
          <Icon size={13} className="text-white/80" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs text-[#e8eef8]">{m.name}</span>
          {m.duration != null && <span className="block text-[10px] text-[#68758a]">{m.duration} s</span>}
        </span>
      </button>
    </li>
  )
}
