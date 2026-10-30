import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import ReactMarkdown from "react-markdown"
import { api } from "@/shared/api-client"
import { HelpButton } from "@/i18n/HelpButton"
import leerBild from "./assets/leer.webp"

interface NoteListItem {
  id: number
  title: string
  updated_at: string
}
interface Note {
  id: number
  title: string
  body: string
  created_at: string
  updated_at: string
}

const BASE = "/modules/notizbuch"

export function NotizbuchPage() {
  const { t } = useTranslation("notizbuch")
  const [list, setList] = useState<NoteListItem[]>([])
  const [active, setActive] = useState<Note | null>(null)
  const [preview, setPreview] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadList = () =>
    api.get<NoteListItem[]>(`${BASE}/notes`).then(setList).catch((e) => setError(String(e)))

  useEffect(() => {
    loadList()
  }, [])

  async function open(id: number) {
    setError(null)
    try {
      setActive(await api.get<Note>(`${BASE}/notes/${id}`))
      setPreview(false)
    } catch (e) {
      setError(String(e))
    }
  }

  async function createNote() {
    setError(null)
    try {
      const note = await api.post<Note>(`${BASE}/notes`, { title: "", body: "" })
      setActive(note)
      setPreview(false)
      await loadList()
    } catch (e) {
      setError(String(e))
    }
  }

  async function save() {
    if (!active) return
    setError(null)
    try {
      const updated = await api.put<Note>(`${BASE}/notes/${active.id}`, {
        title: active.title,
        body: active.body,
      })
      setActive(updated)
      await loadList()
    } catch (e) {
      setError(String(e))
    }
  }

  async function remove() {
    if (!active) return
    setError(null)
    try {
      await api.delete(`${BASE}/notes/${active.id}`)
      setActive(null)
      await loadList()
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div className="flex gap-4 h-full">
      <aside className="w-64 shrink-0 space-y-2">
        <div className="flex items-center gap-2">
          <button
            onClick={createNote}
            className="flex-1 px-3 py-2 rounded-lg bg-[#69d7ff]/15 text-[#69d7ff] text-sm hover:bg-[#69d7ff]/25"
          >
            + {t("new")}
          </button>
          <HelpButton topic="notizbuch" />
        </div>
        {list.length === 0 && <div className="flex flex-col items-center gap-2 py-4 text-center"><img src={leerBild} alt="" loading="lazy" draggable={false} className="mx-auto h-20 w-20 select-none object-contain" /><p className="text-[#9aa7bc] text-sm">{t("empty")}</p></div>}
        {list.map((n) => (
          <button
            key={n.id}
            onClick={() => open(n.id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate ${
              active?.id === n.id ? "bg-[rgb(var(--hh-s-hebung,27_37_54))] text-[#e8eef8]" : "text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
            }`}
          >
            {n.title || t("untitled")}
          </button>
        ))}
      </aside>

      <section className="flex-1 min-w-0">
        {error && (
          <div className="mb-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
            {error}
          </div>
        )}
        {active ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input
                value={active.title}
                placeholder={t("titlePlaceholder")}
                onChange={(e) => setActive({ ...active, title: e.target.value })}
                className="flex-1 px-3 py-2 rounded-lg bg-[rgb(var(--hh-s-box,21_28_43))] border border-[rgb(var(--hh-s-rand,42_54_75))] text-[#e8eef8]"
              />
              <button
                onClick={() => setPreview((p) => !p)}
                className="px-3 py-2 rounded-lg text-sm text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
              >
                {preview ? t("edit") : t("preview")}
              </button>
              <button
                onClick={save}
                className="px-3 py-2 rounded-lg text-sm bg-[#69d7ff]/20 text-[#69d7ff] hover:bg-[#69d7ff]/30"
              >
                {t("save")}
              </button>
              <button
                onClick={remove}
                className="px-3 py-2 rounded-lg text-sm text-rose-300 hover:bg-rose-500/10"
              >
                {t("delete")}
              </button>
            </div>
            {preview ? (
              // react-markdown OHNE rehype-raw: roher HTML im Body wird escaped, kein XSS.
              // Kein rehype-raw ergänzen (würde Stored-XSS über Notiz-Inhalt öffnen).
              <div className="prose prose-invert max-w-none p-3 rounded-lg bg-[rgb(var(--hh-s-box,21_28_43)/0.5)] border border-[rgb(var(--hh-s-rand,42_54_75))]">
                <ReactMarkdown>{active.body}</ReactMarkdown>
              </div>
            ) : (
              <textarea
                value={active.body}
                placeholder={t("bodyPlaceholder")}
                onChange={(e) => setActive({ ...active, body: e.target.value })}
                className="w-full h-[60vh] px-3 py-2 rounded-lg bg-[rgb(var(--hh-s-box,21_28_43))] border border-[rgb(var(--hh-s-rand,42_54_75))] text-[#e8eef8] font-mono text-sm"
              />
            )}
          </div>
        ) : (
          <p className="text-[#9aa7bc] text-sm">{t("empty")}</p>
        )}
      </section>
    </div>
  )
}
