// A3 – Papierkorb des Buchs (unten im Navigator): gelöschte Szenen mit „Wiederherstellen“. Zeigt vorher, wohin die
// Szene zurückkehrt (alte Stelle oder Ende des ersten Kapitels). Lädt erst beim Aufklappen; Leser sehen nur die Liste.
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ChevronDown, ChevronRight, RotateCcw, Trash2 } from "lucide-react"
import { StoryApiError } from "../api"
import { trashApi, whereBack, type TrashChapter, type TrashScene } from "../trashApi"
import type { BookState } from "../useBook"
import { TrashChapters } from "./TrashChapters"

interface Props { state: BookState; onOpenScene: (id: string) => void }

export function TrashScenes({ state, onOpenScene }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<TrashScene[] | null>(null)
  const [chapters, setChapters] = useState<TrashChapter[]>([])   // C1: gelöschte Kapitel
  const [msg, setMsg] = useState("")
  const [error, setError] = useState("")
  const fmt = (iso: string) => new Date(iso).toLocaleString(i18n.language, { dateStyle: "short", timeStyle: "short" })
  const sceneCount = book.parts.reduce((n, p) => n + p.chapters.reduce((m, c) => m + c.scenes.length, 0), 0)

  const load = useCallback(() => Promise.all([trashApi.scenes(projectId, book.id), trashApi.chapters(projectId, book.id)])
    .then(([s, c]) => { setRows(s); setChapters(c) }), [projectId, book.id])
  // Neu laden, wenn aufgeklappt und sich die Zahl der Szenen ändert (z. B. gerade eine gelöscht).
  useEffect(() => {
    if (!open) return
    load().catch((e: unknown) => setError(String(e)))
  }, [open, load, sceneCount])

  const restore = async (s: TrashScene) => {
    setError(""); setMsg("")
    try {
      await state.flush()
      const r = await trashApi.restoreScene(projectId, book.id, s.id)
      state.adoptStructure(r.structure, r.scene)
      setMsg(t(r.placed === "original" ? "trash_restored_original" : "trash_restored_end", { title: s.title }))
      onOpenScene(r.scene.id)
      await load()
    } catch (e) { setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e)) }
  }

  const restoreChapter = async (c: TrashChapter) => {
    setError(""); setMsg("")
    try {
      await state.flush()
      const r = await trashApi.restoreChapter(projectId, book.id, c.id)
      state.adoptStructure(r.structure, r.scenes)
      setMsg(t(r.placed === "original" ? "trash_chapter_restored_original" : "trash_chapter_restored_end", { title: c.title }))
      if (r.scenes[0]) onOpenScene(r.scenes[0].id)
      await load()
    } catch (e) { setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e)) }
  }
  const total = rows ? rows.length + chapters.length : null

  return (
    <section className="st-trash-scenes px-1">
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-500 hover:text-zinc-300">
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        <Trash2 className="h-3.5 w-3.5" />{t("trash_title")}{total !== null ? ` (${total})` : ""}
      </button>
      {open && <TrashChapters rows={chapters} kind={book.kind} canWrite={canWrite} onRestore={(c) => { void restoreChapter(c) }} />}
      {open && rows && rows.length === 0 && chapters.length === 0 && <p className="pl-5 text-xs text-zinc-600">{t("trash_scenes_none")}</p>}
      {open && rows && rows.length > 0 && (
        <ul className="mt-1 space-y-1">
          {rows.map((s) => (
            <li key={s.id} className="st-trash-scene rounded border border-white/5 px-2 py-1 text-xs text-zinc-400">
              <div className="flex items-center gap-2">
                <span className="min-w-0 flex-1 truncate text-zinc-300" title={s.summary}>{s.title || "…"}</span>
                {canWrite && <button onClick={() => { void restore(s) }} title={t("trash_restore")}
                  className="st-trash-restore inline-flex items-center gap-1 text-violet-300 hover:underline">
                  <RotateCcw className="h-3 w-3" />{t("trash_restore")}</button>}
              </div>
              <p className="text-[11px] text-zinc-500">
                {t("trash_deleted_at", { when: fmt(s.deleted_at) })} · {t("words_n", { n: s.words })} ·{" "}
                {whereBack(s) === "original" ? t("trash_back_original", { chapter: s.chapter_title }) : t("trash_back_end")}
              </p>
            </li>
          ))}
        </ul>
      )}
      {msg && <p className="pl-5 text-xs text-emerald-300" role="status">{msg}</p>}
      {error && <p className="pl-5 text-xs text-red-300" role="alert">{error}</p>}
    </section>
  )
}
