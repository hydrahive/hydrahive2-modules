// Bücherliste eines Projekts mit „Weiterschreiben“, „Neues Buch“ und Beispielbuch.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { BookOpen, Feather, Plus, Trash2 } from "lucide-react"
import { draftStore } from "../draftStore"
import { bookWords, findScene, type Book } from "../model"
import { loadSampleBook } from "../sample"
import { NewBookDialog } from "./NewBookDialog"

interface Props {
  projectId: string
  last?: { bookId: string; sceneId: string }
  onOpen: (book: Book, sceneId?: string) => void
}

export function BookList({ projectId, last, onOpen }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const [books, setBooks] = useState<Book[]>(() => draftStore.list(projectId))
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(false)
  const lastBook = last ? books.find((b) => b.id === last.bookId) : undefined
  const lastScene = lastBook && last ? findScene(lastBook, last.sceneId) : null
  const fmt = (iso: string) => new Date(iso).toLocaleString(i18n.language, { dateStyle: "medium", timeStyle: "short" })

  const create = (book: Book) => {
    draftStore.save(projectId, book)
    onOpen(book)
  }
  const sample = async () => {
    setLoading(true)
    try { create(await loadSampleBook()) } finally { setLoading(false) }
  }
  const remove = (b: Book) => {
    if (!confirm(t("delete_confirm", { title: b.title }))) return
    draftStore.remove(projectId, b.id)
    setBooks(draftStore.list(projectId))
  }

  return (
    <div className="space-y-4">
      {lastBook && lastScene && (
        <button onClick={() => onOpen(lastBook, lastScene.scene.id)}
          className="flex w-full items-center gap-4 rounded-xl border border-violet-400/30 bg-violet-500/10 p-4 text-left hover:bg-violet-500/15">
          <Feather className="h-6 w-6 shrink-0 text-violet-300" />
          <div className="min-w-0">
            <div className="text-xs font-semibold uppercase tracking-wider text-violet-300">{t("continue_last")}</div>
            <div className="truncate text-base font-semibold text-zinc-100">{lastBook.title}</div>
            <div className="truncate text-sm text-zinc-400">{lastScene.chapter.title} › {lastScene.scene.title}</div>
          </div>
        </button>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-zinc-300">{t("books")}</h2>
        <div className="flex gap-2">
          <button onClick={sample} disabled={loading}
            className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/5 disabled:opacity-50">
            {t("sample_book")}
          </button>
          <button onClick={() => setCreating(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-violet-500">
            <Plus className="h-4 w-4" />{t("new_book")}
          </button>
        </div>
      </div>

      {books.length === 0 ? (
        <p className="rounded-xl border border-dashed border-white/10 p-8 text-center text-sm text-zinc-500">{t("books_empty")}</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {books.map((b) => (
            <li key={b.id} className="group flex flex-col rounded-xl border border-white/10 bg-zinc-900/50 p-4">
              <div className="flex items-start gap-3">
                <BookOpen className="mt-0.5 h-5 w-5 shrink-0 text-zinc-500" />
                <div className="min-w-0 flex-1">
                  <div className="truncate font-semibold text-zinc-100">{b.title}</div>
                  <div className="text-xs text-zinc-500">
                    {t(`kind_${b.kind}`)} · {t("words_n", { n: bookWords(b).toLocaleString(i18n.language) })}
                    {" · "}{t("edited_at", { when: fmt(b.updatedAt) })}
                  </div>
                  {b.idea && <p className="mt-2 line-clamp-2 text-sm text-zinc-400">{b.idea}</p>}
                </div>
              </div>
              <div className="mt-3 flex justify-end gap-2">
                <button onClick={() => remove(b)} title={t("delete_book")}
                  className="rounded-lg p-1.5 text-zinc-500 opacity-60 hover:bg-red-500/10 hover:text-red-300 group-hover:opacity-100">
                  <Trash2 className="h-4 w-4" />
                </button>
                <button onClick={() => onOpen(b)}
                  className="rounded-lg border border-white/10 px-3 py-1 text-sm text-zinc-200 hover:bg-white/5">{t("open")}</button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {creating && <NewBookDialog onCancel={() => setCreating(false)} onCreate={create} />}
    </div>
  )
}
