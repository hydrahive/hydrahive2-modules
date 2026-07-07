import { useEffect, useState } from "react"
import {
  deleteRun, getRun, listModels, listRuns, startRun,
  type ModelInfo, type Run, type RunListItem,
} from "./api"
import { HelpButton } from "@/i18n/HelpButton"
import { LiveProgress } from "./LiveProgress"
import { ReportFrame } from "./ReportFrame"
import { RunList, type RunFilter } from "./RunList"

const POLL_MS = 1200

export function DeepResearchPage() {
  const [list, setList] = useState<RunListItem[]>([])
  const [active, setActive] = useState<Run | null>(null)
  const [question, setQuestion] = useState("")
  const [depth, setDepth] = useState(6)
  const [category, setCategory] = useState("")
  const [model, setModel] = useState("")
  const [models, setModels] = useState<ModelInfo[]>([])
  const [filter, setFilter] = useState<RunFilter>("all")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadList = () => listRuns().then(setList).catch((e) => setError(String(e)))

  useEffect(() => {
    loadList()
    listModels().then((d) => setModels(d.models)).catch(() => {})
  }, [])

  const inFlight = (s?: string) => s === "queued" || s === "running"
  const anyInFlight = list.some((r) => inFlight(r.status)) || inFlight(active?.status)

  useEffect(() => {
    if (!anyInFlight) return
    const t = window.setInterval(() => {
      loadList()
      if (active && inFlight(active.status)) getRun(active.id).then(setActive).catch(() => {})
    }, POLL_MS)
    return () => window.clearInterval(t)
  }, [anyInFlight, active?.id, active?.status])

  async function start() {
    const q = question.trim()
    if (!q || submitting) return
    setError(null)
    setSubmitting(true)
    try {
      const { run_id } = await startRun(q, { model: model || undefined, max_rounds: depth, category: category || undefined })
      setQuestion("")
      await loadList()
      setActive(await getRun(run_id))
    } catch (e) {
      setError(String(e))
    } finally {
      setSubmitting(false)
    }
  }

  async function open(id: string) {
    setError(null)
    try {
      setActive(await getRun(id))
    } catch (e) {
      setError(String(e))
    }
  }

  async function del(id: string) {
    try {
      await deleteRun(id)
      if (active?.id === id) setActive(null)
      await loadList()
    } catch (e) {
      setError(String(e))
    }
  }

  const ctl = "px-2 py-2 rounded-xl bg-zinc-900 border border-white/10 text-zinc-300 text-xs"
  return (
    <div className="max-w-6xl mx-auto h-full flex gap-5">
      <aside className="w-72 shrink-0 flex flex-col">
        <div className="flex items-center gap-2 mb-2">
          <h1 className="text-sm font-semibold text-zinc-200">Deep Research</h1>
          <HelpButton topic="deepresearch" />
        </div>
        <textarea
          value={question}
          placeholder="Worüber soll recherchiert werden?"
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) start() }}
          className="w-full h-24 px-3 py-2 rounded-xl bg-zinc-900 border border-white/10 text-zinc-100 text-sm resize-none"
        />
        <select value={model} onChange={(e) => setModel(e.target.value)} className={`${ctl} mt-2 w-full`} title="Modell">
          <option value="">Standard-Modell</option>
          {models.map((m) => (
            <option key={m.id} value={m.id}>{m.label}{m.is_free ? " · gratis" : ""}</option>
          ))}
        </select>
        <div className="flex gap-2 mt-2">
          <select value={depth} onChange={(e) => setDepth(Number(e.target.value))} className={`${ctl} flex-1`} title="Tiefe">
            <option value={3}>Schnell · 3</option>
            <option value={6}>Standard · 6</option>
            <option value={8}>Tief · 8</option>
          </select>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className={`${ctl} flex-1`} title="Kategorie">
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
          disabled={submitting || !question.trim()}
          className="mt-2 w-full px-3 py-2.5 rounded-xl text-sm font-medium bg-orange-500/15 text-orange-300 hover:bg-orange-500/25 disabled:opacity-40"
        >
          {submitting ? "Starte …" : "Recherche starten"}
        </button>

        <div className="flex-1 overflow-auto mt-1">
          <RunList runs={list} activeId={active?.id ?? null} filter={filter} onFilter={setFilter} onSelect={open} onDelete={del} />
        </div>
      </aside>

      <section className="flex-1 min-w-0 overflow-auto">
        {error && (
          <div className="mb-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">{error}</div>
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
        {active && inFlight(active.status) && <LiveProgress run={active} />}
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
