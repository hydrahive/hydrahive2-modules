import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"

interface Note {
  id: number
  text: string
  created_at: string
}

export function ExamplePage() {
  const { t } = useTranslation("example")
  const [notes, setNotes] = useState<Note[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchNotes = () => {
    setLoading(true)
    setError(null)
    api
      .get<Note[]>("/modules/example/notes")
      .then((data) => setNotes(data))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchNotes()
  }, [])

  const handleAdd = () => {
    const text = input.trim()
    if (!text) return
    setAdding(true)
    setError(null)
    api
      .post<Note>("/modules/example/notes", { text })
      .then(() => {
        setInput("")
        fetchNotes()
      })
      .catch((e) => setError(String(e)))
      .finally(() => setAdding(false))
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      <h1 className="text-lg font-semibold text-[#e8eef8]">{t("title")}</h1>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder={t("placeholder")}
          className="flex-1 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-3 py-2 text-sm text-[#e8eef8] placeholder-[#9aa7bc] focus:outline-none focus:ring-1 focus:ring-[rgb(var(--hh-s-rand-hover,70_97_127))]"
        />
        <button
          onClick={handleAdd}
          disabled={adding || !input.trim()}
          className="rounded-lg bg-[rgb(var(--hh-s-hebung,27_37_54))] px-4 py-2 text-sm text-[#e8eef8] hover:bg-[rgb(var(--hh-s-rand-hover,70_97_127))] disabled:opacity-40 transition-colors"
        >
          {t("add")}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="h-24 rounded-xl bg-[rgb(var(--hh-s-box,21_28_43)/0.5)] animate-pulse" />
      ) : notes.length === 0 ? (
        <p className="text-sm text-[#9aa7bc]">{t("empty")}</p>
      ) : (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] px-4 py-3 text-sm text-[#e8eef8]"
            >
              {note.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
