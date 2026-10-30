import { useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { tonstudioApi } from "./api"
import { errText } from "./errors"
import { LibraryCard } from "./LibraryCard"
import { groupLibrary, type Sort } from "./libraryView"
import { useSinglePlayer } from "./useSinglePlayer"
import type { LibraryItem } from "./types"

interface Props {
  projectId: string
  items: LibraryItem[]
  onChanged: () => void
}

/** Bibliothek als kompakte Kacheln, gegliedert nach Herkunft, sortier- und filterbar. Ein Player für alle. */
export function Library({ projectId, items, onChanged }: Props) {
  const { t } = useTranslation("tonstudio")
  const fileRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [sort, setSort] = useState<Sort>("new")
  const [query, setQuery] = useState("")
  const player = useSinglePlayer(projectId)

  const grouped = useMemo(() => groupLibrary(items, sort, query), [items, sort, query])

  async function upload(file: File | undefined) {
    if (!file) return
    setBusy(true)
    setError("")
    try {
      await tonstudioApi.upload(projectId, file)
      onChanged()
    } catch (e) {
      setError(errText(e))
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  async function remove(rel: string) {
    if (!confirm(t("clip_delete_confirm"))) return
    try {
      if (player.current === rel) player.stop()
      await tonstudioApi.deleteClip(projectId, rel)
      onChanged()
    } catch (e) {
      setError(errText(e))
    }
  }

  async function rename(it: LibraryItem) {
    const next = prompt(t("rename"), it.named === false ? "" : it.name)
    if (next === null) return
    try {
      await tonstudioApi.setLabel(projectId, it.source_rel, next.trim())
      onChanged()
    } catch (e) {
      setError(errText(e))
    }
  }

  const ctl = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1 text-xs text-[#e8eef8]"
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("library_search")} className={`${ctl} min-w-[140px] flex-1`} />
        <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label={t("sort")} className={ctl}>
          <option value="new">{t("sort_new")}</option>
          <option value="name">{t("sort_name")}</option>
          <option value="length">{t("sort_length")}</option>
        </select>
        <input ref={fileRef} type="file" accept="audio/*,.mp3,.wav,.flac,.ogg,.m4a" className="hidden" onChange={(e) => upload(e.target.files?.[0])} />
        <button onClick={() => fileRef.current?.click()} disabled={busy} className={`${ctl} hover:bg-[#1c2940] disabled:opacity-40`}>
          {busy ? t("uploading") : `⬆️ ${t("upload")}`}
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {items.length === 0 && <p className="text-xs text-[#9aa7bc]">{t("library_empty")}</p>}
      {grouped.map(({ g, list }) => (
        <div key={g} className="flex flex-col gap-1.5">
          <h4 className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#9aa7bc]">
            {t(`group_${g}`)} <span className="font-normal text-[#9aa7bc]">· {list.length}</span>
          </h4>
          <ul className="grid gap-1.5 [grid-template-columns:repeat(auto-fill,minmax(220px,1fr))]">
            {list.map((it) => (
              <LibraryCard key={it.source_rel} item={it} playing={player.current === it.source_rel && player.playing}
                progress={player.current === it.source_rel ? player.progress : 0}
                onToggle={() => player.toggle(it.source_rel)} onSeek={(f) => player.seek(it.source_rel, f)}
                onDelete={it.origin !== "project" ? () => remove(it.source_rel) : undefined} onRename={() => rename(it)} />
            ))}
          </ul>
        </div>
      ))}
      {player.element}
    </section>
  )
}
