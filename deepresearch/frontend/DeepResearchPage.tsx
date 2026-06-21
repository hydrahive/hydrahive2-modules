import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import ReactMarkdown from "react-markdown"
import { api } from "@/shared/api-client"

interface RunListItem {
  id: string
  question: string
  status: string
  created_at: string
}

interface Source {
  url: string
  title: string
  image: string
}

interface RunResult {
  markdown: string
  sources: Source[]
  stats: Record<string, unknown>
  category: string
}

interface Run {
  id: string
  question: string
  status: string // running | done | error
  category: string
  progress: Record<string, unknown>
  result: RunResult | null
  error: string | null
}

const BASE = "/modules/deepresearch"
const POLL_MS = 1500

function statusIcon(status: string): string {
  if (status === "done") return "✓"
  if (status === "error") return "✕"
  return "⋯"
}

function progressLine(p: Record<string, unknown>): string {
  const round = typeof p.round === "number" ? p.round : undefined
  const urls = typeof p.urls === "number" ? p.urls : undefined
  if (!round) return ""
  return ` · Runde ${round}${urls ? `, ${urls} Quellen` : ""}`
}

export function DeepResearchPage() {
  const { t } = useTranslation("deepresearch")
  const [list, setList] = useState<RunListItem[]>([])
  const [active, setActive] = useState<Run | null>(null)
  const [question, setQuestion] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)

  const loadList = () =>
    api.get<RunListItem[]>(`${BASE}/runs`).then(setList).catch((e) => setError(String(e)))

  useEffect(() => {
    loadList()
    return () => {
      if (pollRef.current) window.clearTimeout(pollRef.current)
    }
  }, [])

  function poll(id: string) {
    api
      .get<Run>(`${BASE}/runs/${id}`)
      .then((run) => {
        setActive(run)
        if (run.status === "running") {
          pollRef.current = window.setTimeout(() => poll(id), POLL_MS)
        } else {
          setBusy(false)
          loadList()
        }
      })
      .catch((e) => {
        setError(String(e))
        setBusy(false)
      })
  }

  async function start() {
    const q = question.trim()
    if (!q || busy) return
    setError(null)
    setBusy(true)
    setActive(null)
    try {
      const { run_id } = await api.post<{ run_id: string }>(`${BASE}/runs`, { question: q })
      setQuestion("")
      await loadList()
      poll(run_id)
    } catch (e) {
      setError(String(e))
      setBusy(false)
    }
  }

  async function open(id: string) {
    setError(null)
    if (pollRef.current) window.clearTimeout(pollRef.current)
    try {
      const run = await api.get<Run>(`${BASE}/runs/${id}`)
      setActive(run)
      if (run.status === "running") {
        setBusy(true)
        poll(id)
      }
    } catch (e) {
      setError(String(e))
    }
  }

  const running = active?.status === "running" || busy

  return (
    <div className="flex gap-4 h-full">
      <aside className="w-72 shrink-0 space-y-3">
        <textarea
          value={question}
          placeholder={t("placeholder")}
          onChange={(e) => setQuestion(e.target.value)}
          className="w-full h-24 px-3 py-2 rounded-lg bg-zinc-900 border border-white/10 text-zinc-100 text-sm"
        />
        <button
          onClick={start}
          disabled={running || !question.trim()}
          className="w-full px-3 py-2 rounded-lg bg-sky-500/15 text-sky-300 text-sm hover:bg-sky-500/25 disabled:opacity-40"
        >
          {running ? t("running") : t("start")}
        </button>

        <div className="space-y-1 pt-2 border-t border-white/5">
          {list.length === 0 && <p className="text-zinc-600 text-sm py-2">{t("empty")}</p>}
          {list.map((r) => (
            <button
              key={r.id}
              onClick={() => open(r.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate ${
                active?.id === r.id ? "bg-white/10 text-zinc-100" : "text-zinc-400 hover:bg-white/5"
              }`}
            >
              <span className="mr-2 text-zinc-500">{statusIcon(r.status)}</span>
              {r.question || t("untitled")}
            </button>
          ))}
        </div>
      </aside>

      <section className="flex-1 min-w-0 overflow-auto">
        {error && (
          <div className="mb-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
            {error}
          </div>
        )}
        {!active && <p className="text-zinc-600 text-sm">{t("hint")}</p>}
        {active && (
          <div className="space-y-4">
            <h1 className="text-xl font-semibold text-zinc-100">{active.question}</h1>

            {active.status === "running" && (
              <div className="p-3 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-300 text-sm">
                {t("working")}
                {progressLine(active.progress)} …
              </div>
            )}

            {active.status === "error" && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
                {active.error || t("failed")}
              </div>
            )}

            {active.status === "done" && active.result && (
              <>
                {/* Kein rehype-raw: roher HTML im Bericht wird escaped (Bericht stammt aus
                    ungetrustetem Web-Inhalt). Der hübsche HTML-Report kommt später separat. */}
                <article className="prose prose-invert max-w-none">
                  <ReactMarkdown>{active.result.markdown}</ReactMarkdown>
                </article>

                {active.result.sources.length > 0 && (
                  <div className="pt-3 border-t border-white/5">
                    <h2 className="text-sm font-semibold text-zinc-400 mb-2">
                      {t("sources")} ({active.result.sources.length})
                    </h2>
                    <ol className="space-y-1 text-sm">
                      {active.result.sources.map((s, i) => (
                        <li key={s.url} className="text-zinc-400">
                          {i + 1}.{" "}
                          <a
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sky-400 hover:underline"
                          >
                            {s.title || s.url}
                          </a>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
