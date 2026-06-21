import { useEffect, useRef, useState } from "react"
import { getRun, listRuns, startRun, type Run, type RunListItem } from "./api"
import { LiveProgress } from "./LiveProgress"
import { ReportFrame } from "./ReportFrame"

const POLL_MS = 1200

function statusIcon(status: string): string {
  if (status === "done") return "✓"
  if (status === "error") return "✕"
  return "⋯"
}

export function DeepResearchPage() {
  const [list, setList] = useState<RunListItem[]>([])
  const [active, setActive] = useState<Run | null>(null)
  const [question, setQuestion] = useState("")
  const [depth, setDepth] = useState(6)
  const [category, setCategory] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)

  const loadList = () => listRuns().then(setList).catch((e) => setError(String(e)))

  function stopPoll() {
    if (pollRef.current) {
      window.clearTimeout(pollRef.current)
      pollRef.current = null
    }
  }

  useEffect(() => {
    loadList()
    return stopPoll
  }, [])

  function poll(id: string) {
    getRun(id)
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
    stopPoll()
    try {
      const { run_id } = await startRun(q, { max_rounds: depth, category: category || undefined })
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
    stopPoll()
    try {
      const run = await getRun(id)
      setActive(run)
      if (run.status === "running") {
        setBusy(true)
        poll(id)
      }
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div className="flex gap-5 h-full">
      <aside className="w-72 shrink-0 space-y-3">
        <textarea
          value={question}
          placeholder="Worüber soll recherchiert werden?"
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) start()
          }}
          className="w-full h-28 px-3 py-2 rounded-xl bg-zinc-900 border border-white/10 text-zinc-100 text-sm resize-none"
        />
        <div className="flex gap-2">
          <select
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="flex-1 px-2 py-2 rounded-xl bg-zinc-900 border border-white/10 text-zinc-300 text-xs"
            title="Recherche-Tiefe"
          >
            <option value={3}>Schnell · 3 Runden</option>
            <option value={6}>Standard · 6 Runden</option>
            <option value={8}>Tief · 8 Runden</option>
          </select>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="flex-1 px-2 py-2 rounded-xl bg-zinc-900 border border-white/10 text-zinc-300 text-xs"
            title="Kategorie"
          >
            <option value="">Auto-Kategorie</option>
            <option value="product">Produkt</option>
            <option value="comparison">Vergleich</option>
            <option value="howto">How-to</option>
            <option value="factcheck">Faktencheck</option>
            <option value="general">Allgemein</option>
          </select>
        </div>
        <button
          onClick={start}
          disabled={busy || !question.trim()}
          className="w-full px-3 py-2.5 rounded-xl text-sm font-medium bg-orange-500/15 text-orange-300 hover:bg-orange-500/25 disabled:opacity-40"
        >
          {busy ? "Recherchiere …" : "Recherche starten"}
        </button>

        <div className="space-y-1 pt-3 border-t border-white/5">
          {list.length === 0 && <p className="text-zinc-600 text-sm py-1">Noch keine Recherchen</p>}
          {list.map((r) => (
            <button
              key={r.id}
              onClick={() => open(r.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate ${
                active?.id === r.id ? "bg-white/10 text-zinc-100" : "text-zinc-400 hover:bg-white/5"
              }`}
            >
              <span className="mr-2 text-zinc-500">{statusIcon(r.status)}</span>
              {r.question || "Ohne Titel"}
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

        {!active && (
          <div className="h-full flex items-center justify-center text-center">
            <div className="max-w-sm">
              <div className="text-4xl mb-3">🔭</div>
              <p className="text-zinc-400 text-sm">
                Stelle links eine Frage. Deep Research durchsucht das Web in mehreren Runden und
                erstellt einen bebilderten, quellenbasierten Bericht.
              </p>
            </div>
          </div>
        )}

        {active?.status === "running" && <LiveProgress run={active} />}

        {active?.status === "error" && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
            {active.error || "Recherche fehlgeschlagen"}
          </div>
        )}

        {active?.status === "done" && <ReportFrame runId={active.id} />}
      </section>
    </div>
  )
}
