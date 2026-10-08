// Bücherliste eines Projekts (vom Server) mit „Weiterschreiben“, „Neues Buch“, Beispielbuch und
// Übernahme der Bücher aus dem Entwurf 0.1.0.
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { BookOpen, Feather, FolderInput, Plus, Trash2 } from "lucide-react"
import { storyApi, type ServerBookInfo } from "../api"
import { afterCreate, afterMove, bookProjectApi, canMove, errorText, type BookPlace } from "../bookProject"
import { lastPlace } from "../lastPlace"
import type { BookKind } from "../model"
import { loadSampleBook } from "../sample"
import { toImport } from "../serverBook"
import { DraftImport } from "./DraftImport"
import { NewBookDialog } from "./NewBookDialog"

interface Props {
  projectId: string
  projectName: string
  onOpen: (bookId: string, sceneId?: string) => void
  /** T1c: Buch wurde als eigenes Projekt angelegt → Seite wechselt dorthin und öffnet es. */
  onProjectCreated: (projectId: string, bookId: string) => void
  canCreateProject: boolean
  /** Projekt gehört genau zu einem Buch (eigenes Projekt mit Team) → Hinweis beim Löschen. */
  bookProject?: boolean
}

export function BookList({ projectId, projectName, onOpen, onProjectCreated, canCreateProject, bookProject = false }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const [books, setBooks] = useState<ServerBookInfo[] | null>(null)
  const [creating, setCreating] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const last = lastPlace.get(projectId)
  const lastBook = last ? books?.find((b) => b.id === last.bookId) : undefined
  const fmt = (iso: string) => new Date(iso).toLocaleString(i18n.language, { dateStyle: "medium", timeStyle: "short" })
  const fail = (e: unknown) => setError(errorText(t, e))

  const load = useCallback(() => {
    storyApi.listBooks(projectId).then((b) => { setBooks(b); setError("") })
      .catch((e: unknown) => { setBooks([]); setError(e instanceof Error ? e.message : String(e)) })
  }, [projectId])
  useEffect(load, [load])

  const run = async (fn: () => Promise<string>) => {
    setBusy(true)
    try { onOpen(await fn()) } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const create = async (f: { title: string; kind: BookKind; language: string; audience: string; idea: string }, place: BookPlace) => {
    if (place === "current") return run(async () => (await storyApi.createBook(projectId, f)).id)
    setBusy(true)
    try {
      const made = afterCreate(await bookProjectApi.create(f))
      onProjectCreated(made.projectId, made.bookId)
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const sample = () => run(async () => (await storyApi.importBook(projectId, toImport(await loadSampleBook()))).id)
  const moveOut = async (b: ServerBookInfo) => {
    if (!confirm(t("move_confirm", { title: b.title }))) return
    setBusy(true)
    try {
      const moved = afterMove(await bookProjectApi.move(projectId, b.id))
      lastPlace.clear(projectId, b.id)
      onProjectCreated(moved.projectId, moved.bookId)
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const remove = async (b: ServerBookInfo) => {
    if (!confirm(t(bookProject ? "delete_confirm_book_project" : "delete_confirm", { title: b.title }))) return
    try {
      await storyApi.deleteBook(projectId, b.id)
      lastPlace.clear(projectId, b.id)
      load()
    } catch (e) { fail(e) }
  }

  return (
    <div className="space-y-4">
      <DraftImport projectId={projectId} onDone={load} />
      {lastBook && last && (
        <button onClick={() => onOpen(lastBook.id, last.sceneId)}
          className="flex w-full items-center gap-4 rounded-xl border border-violet-400/30 bg-violet-500/10 p-4 text-left hover:bg-violet-500/15">
          <Feather className="h-6 w-6 shrink-0 text-violet-300" />
          <div className="min-w-0">
            <div className="text-xs font-semibold uppercase tracking-wider text-violet-300">{t("continue_last")}</div>
            <div className="truncate text-base font-semibold text-zinc-100">{lastBook.title}</div>
          </div>
        </button>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-zinc-300">{t("books")}</h2>
        <div className="flex gap-2">
          <button onClick={() => { void sample() }} disabled={busy}
            className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/5 disabled:opacity-50">
            {t("sample_book")}
          </button>
          <button onClick={() => setCreating(true)} disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">
            <Plus className="h-4 w-4" />{t("new_book")}
          </button>
        </div>
      </div>
      {error && <p className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200" role="alert">{error}</p>}

      {books === null ? <p className="text-sm text-zinc-500">…</p> : books.length === 0 ? (
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
                    {t(`kind_${b.kind}`)} · {t("words_n", { n: b.words.toLocaleString(i18n.language) })}
                    {" · "}{t("edited_at", { when: fmt(b.updated_at) })}
                  </div>
                  {b.idea && <p className="mt-2 line-clamp-2 text-sm text-zinc-400">{b.idea}</p>}
                </div>
              </div>
              <div className="mt-3 flex justify-end gap-2">
                {canMove(canCreateProject, b) && (
                  <button onClick={() => { void moveOut(b) }} disabled={busy} title={t("move_hint")}
                    className="st-move-book mr-auto inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-zinc-400 hover:bg-white/5 hover:text-zinc-200 disabled:opacity-50">
                    <FolderInput className="h-3.5 w-3.5" />{t("move_book")}
                  </button>
                )}
                <button onClick={() => { void remove(b) }} title={t("delete_book")} aria-label={t("delete_book")}
                  className="rounded-lg p-1.5 text-zinc-500 opacity-60 hover:bg-red-500/10 hover:text-red-300 group-hover:opacity-100">
                  <Trash2 className="h-4 w-4" />
                </button>
                <button onClick={() => onOpen(b.id)}
                  className="rounded-lg border border-white/10 px-3 py-1 text-sm text-zinc-200 hover:bg-white/5">{t("open")}</button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {busy && <p className="text-sm text-zinc-500" role="status">{t("nb_creating")}</p>}
      {creating && <NewBookDialog onCancel={() => setCreating(false)} canCreateProject={canCreateProject} currentProjectName={projectName}
        onCreate={(f, place) => { setCreating(false); void create(f, place) }} />}
    </div>
  )
}
