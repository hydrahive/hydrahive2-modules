// A3 – Papierkorb des Projekts (unter der Bücherliste): gelöschte Bücher mit „Wiederherstellen“; Sicherungen nach
// einem Umzug nur zur Information (das Buch lebt im neuen Projekt weiter). Lädt erst beim Aufklappen.
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ChevronDown, ChevronRight, RotateCcw, Trash2 } from "lucide-react"
import { StoryApiError } from "../api"
import { sortBooks, trashApi, type TrashBook } from "../trashApi"

interface Props { projectId: string; canWrite: boolean; onRestored: (bookId: string) => void }

export function TrashBooks({ projectId, canWrite, onRestored }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<TrashBook[] | null>(null)
  const [msg, setMsg] = useState("")
  const [error, setError] = useState("")
  const fmt = (iso: string) => new Date(iso).toLocaleString(i18n.language, { dateStyle: "medium", timeStyle: "short" })

  const load = useCallback(() => trashApi.books(projectId).then((r) => setRows(sortBooks(r))), [projectId])
  useEffect(() => {
    if (!open) return
    load().catch((e: unknown) => setError(String(e)))
  }, [open, load])

  const restore = async (b: TrashBook) => {
    setError(""); setMsg("")
    try {
      await trashApi.restoreBook(projectId, b.id)
      setMsg(t("trash_book_restored", { title: b.title }))
      onRestored(b.book_id)
      await load()
    } catch (e) { setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e)) }
  }

  return (
    <section className="st-trash-books space-y-1">
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300">
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        <Trash2 className="h-3.5 w-3.5" />{t("trash_title")}{rows ? ` (${rows.length})` : ""}
      </button>
      {open && rows && rows.length === 0 && <p className="text-xs text-zinc-600">{t("trash_books_none")}</p>}
      {open && rows && rows.length > 0 && (
        <ul className="space-y-1">
          {rows.map((b) => (
            <li key={b.id} className={`st-trash-book st-trash-${b.kind} flex flex-wrap items-center gap-2 rounded border border-white/5 px-3 py-2 text-sm`}>
              <span className="min-w-0 flex-1 truncate text-zinc-200">{b.title}</span>
              <span className="text-xs text-zinc-500">{t("trash_scenes_n", { n: b.scenes, words: b.words.toLocaleString(i18n.language) })} · {t("trash_deleted_at", { when: fmt(b.deleted_at) })}</span>
              {b.restorable && canWrite && <button onClick={() => { void restore(b) }}
                className="st-trash-restore inline-flex items-center gap-1 text-xs text-violet-300 hover:underline">
                <RotateCcw className="h-3.5 w-3.5" />{t("trash_restore")}</button>}
              {!b.restorable && <span className="w-full text-[11px] text-zinc-500">{t("trash_moved")}</span>}
            </li>
          ))}
        </ul>
      )}
      {msg && <p className="text-xs text-emerald-300" role="status">{msg}</p>}
      {error && <p className="text-xs text-red-300" role="alert">{error}</p>}
    </section>
  )
}
