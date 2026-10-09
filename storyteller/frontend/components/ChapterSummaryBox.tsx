// A5c – Kasten „Kapitel ‚…‘“ im Reiter „Szene“: Kapitel-Zusammenfassung lesen, bearbeiten (speichert beim Verlassen
// des Felds) und per Knopf aus den Szenen-Zusammenfassungen erzeugen lassen. Grundregel wie bei allen KI-Vorschlägen:
// der erzeugte Text ändert nichts, bis er übernommen wird. Nichts passiert automatisch.
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Sparkles } from "lucide-react"
import { StoryApiError } from "../api"
import { chapterSummaryApi, isDirty, type ChapterSummary } from "../chapterSummary"
import type { BookState } from "../useBook"

const field = "w-full rounded-lg border border-white/10 bg-zinc-950 px-2.5 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-600"
const EMPTY: ChapterSummary = { summary: "", version: 0, updated_at: "" }

interface Props { state: BookState; chapterId: string; chapterTitle: string }

export function ChapterSummaryBox({ state, chapterId, chapterTitle }: Props) {
  const { t } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const [saved, setSaved] = useState<ChapterSummary>(EMPTY)
  const [draft, setDraft] = useState("")
  const [proposal, setProposal] = useState<string | null>(null)
  const [busy, setBusy] = useState<"" | "load" | "save" | "generate">("load")
  const [error, setError] = useState("")

  useEffect(() => {
    let alive = true
    chapterSummaryApi.all(projectId, book.id)
      .then((r) => { if (!alive) return; const s = r.chapters[chapterId] ?? EMPTY; setSaved(s); setDraft(s.summary) })
      .catch((e) => { if (alive) setError(message(e, t)) })
      .finally(() => { if (alive) setBusy("") })
    return () => { alive = false }
  }, [projectId, book.id, chapterId, t])

  const save = async (text: string) => {
    if (!canWrite || !isDirty(text, saved.summary)) return
    setBusy("save"); setError("")
    try {
      const s = await chapterSummaryApi.save(projectId, book.id, chapterId, text, saved.version)
      setSaved(s); setDraft(s.summary)
    } catch (e) {
      if (e instanceof StoryApiError && e.status === 409) {
        setSaved((e.current as ChapterSummary | undefined) ?? EMPTY)   // eigener Text bleibt im Feld stehen
        setError(t("chapter_summary_conflict"))
      } else setError(message(e, t))
    } finally { setBusy("") }
  }

  const generate = async () => {
    setBusy("generate"); setError("")
    try {
      await state.flush()   // Server braucht die aktuellen Szenen-Zusammenfassungen
      setProposal((await chapterSummaryApi.generate(projectId, book.id, chapterId, book.model || undefined)).summary)
    } catch (e) { setError(message(e, t)) } finally { setBusy("") }
  }

  const accept = async () => {
    if (proposal === null) return
    setDraft(proposal); setProposal(null)
    await save(proposal)
  }

  return (
    <section className="space-y-1.5 rounded-lg border border-white/10 bg-white/[0.02] p-2.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="truncate text-xs font-semibold text-zinc-400">{t("chapter_summary_title", { title: chapterTitle })}</h3>
        {canWrite && proposal === null && (
          <button onClick={() => { void generate() }} disabled={!!busy} title={t("chapter_summary_generate_hint")}
            className="flex shrink-0 items-center gap-1 rounded px-2 py-0.5 text-xs text-violet-300 hover:bg-violet-500/10 disabled:opacity-40">
            {busy === "generate" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
            {t("chapter_summary_generate")}
          </button>
        )}
      </div>
      {proposal !== null && (
        <div className="space-y-1.5 rounded-lg border border-violet-400/30 bg-violet-500/5 p-2">
          <p className="text-[11px] font-semibold text-violet-300">{t("chapter_summary_proposal")}</p>
          <p className="whitespace-pre-wrap text-sm text-zinc-200">{proposal}</p>
          <div className="flex gap-2">
            <button onClick={() => { void accept() }} disabled={!!busy}
              className="rounded bg-violet-600 px-2.5 py-0.5 text-xs text-white hover:bg-violet-500 disabled:opacity-40">{t("chapter_summary_accept")}</button>
            <button onClick={() => setProposal(null)} disabled={!!busy}
              className="rounded px-2.5 py-0.5 text-xs text-zinc-400 hover:bg-white/5">{t("chapter_summary_discard")}</button>
          </div>
        </div>
      )}
      <textarea className={`${field} min-h-[64px]`} value={draft} readOnly={!canWrite} disabled={busy === "load"}
        placeholder={t("chapter_summary_ph")} maxLength={4000}
        onChange={(e) => setDraft(e.target.value)} onBlur={() => { void save(draft) }} />
      <p className="text-[11px] text-zinc-600">{busy === "save" ? t("chapter_summary_saving") : t("chapter_summary_hint")}</p>
      {error && <p className="text-xs text-red-300">{error}</p>}
    </section>
  )
}

function message(e: unknown, t: (k: string, o?: Record<string, unknown>) => string): string {
  if (e instanceof StoryApiError) {
    if (["summaries_required", "ai_busy", "rate_limited", "llm_empty"].includes(e.code)) return t(`chapter_summary_err_${e.code}`)
    return t("ai_err_llm_failed", { message: e.message || e.code })
  }
  return t("ai_err_llm_failed", { message: String(e) })
}
