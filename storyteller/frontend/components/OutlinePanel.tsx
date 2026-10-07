// Ghostwriter G2 – Gliederung aus Idee (Spec §9.1): Idee + Umfang → KI-Vorschlag → hier bearbeiten
// (Titel, Zusammenfassungen, streichen) → übernehmen. Nichts wird gespeichert, bis „Übernehmen“.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Check, ListTree, Loader2, Trash2, X } from "lucide-react"
import { StoryApiError } from "../api"
import { editScene, outlineProblem, outlineStats, removeChapter, removeScene, renameChapter, type Outline } from "../outlineModel"
import { runApi } from "../runApi"
import type { BookState } from "../useBook"

const field = "w-full rounded border border-white/10 bg-zinc-950 px-2 py-1 text-xs text-zinc-100"

export function OutlinePanel({ state }: { state: BookState }) {
  const { t } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const [open, setOpen] = useState(false)
  const [idea, setIdea] = useState(book.idea)
  const [hints, setHints] = useState("")
  const [chapters, setChapters] = useState(5)
  const [perChapter, setPerChapter] = useState(3)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [draft, setDraft] = useState<Outline | null>(null)
  const fail = (e: unknown) => setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e))

  const generate = async () => {
    setBusy(true); setError("")
    try { setDraft(await runApi.outline(projectId, book.id, { idea, hints, chapters, scenes_per_chapter: perChapter })) }
    catch (e) { fail(e) } finally { setBusy(false) }
  }
  const apply = async () => {
    if (!draft) return
    setBusy(true); setError("")
    try {
      await state.flush()
      const version = state.structureVersion()
      const r = await runApi.applyOutline(projectId, book.id, draft, version)
      state.adoptStructure(r.structure, Object.values(r.scenes))
      setDraft(null); setOpen(false)
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const problem = draft ? outlineProblem(draft) : null

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} disabled={!canWrite}
        className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-200 hover:bg-white/5 disabled:opacity-40">
        <ListTree className="h-4 w-4" />{t("outline_open")}
      </button>
    )
  }
  return (
    <section className="st-outline space-y-2 rounded-xl border border-white/10 p-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">{t("outline_title")}</h3>
      {!draft && (
        <div className="space-y-2 text-xs text-zinc-400">
          <label className="block space-y-1"><span>{t("outline_idea")}</span>
            <textarea className={`${field} min-h-[60px]`} value={idea} maxLength={4000} onChange={(e) => setIdea(e.target.value)} /></label>
          <label className="block space-y-1"><span>{t("outline_hints")}</span>
            <input className={field} value={hints} maxLength={2000} placeholder={t("outline_hints_ph")} onChange={(e) => setHints(e.target.value)} /></label>
          <div className="flex gap-2">
            <label className="flex items-center gap-1">{t("outline_chapters")}
              <input type="number" min={1} max={40} value={chapters} className={`${field} w-14`} onChange={(e) => setChapters(Math.min(40, Math.max(1, Number(e.target.value) || 1)))} /></label>
            <label className="flex items-center gap-1">{t("outline_per_chapter")}
              <input type="number" min={1} max={8} value={perChapter} className={`${field} w-12`} onChange={(e) => setPerChapter(Math.min(8, Math.max(1, Number(e.target.value) || 1)))} /></label>
          </div>
          <div className="flex gap-2">
            <button onClick={() => { void generate() }} disabled={busy || !idea.trim()}
              className="inline-flex flex-1 items-center justify-center gap-1 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ListTree className="h-4 w-4" />}{t("outline_generate")}
            </button>
            <button onClick={() => setOpen(false)} className="rounded-lg border border-white/10 px-2 text-zinc-300"><X className="h-4 w-4" /></button>
          </div>
        </div>
      )}
      {draft && (
        <div className="space-y-2">
          <p className="text-xs text-zinc-400">{t("outline_review", outlineStats(draft))}</p>
          <ol className="max-h-96 space-y-2 overflow-y-auto pr-1">
            {draft.chapters.map((c, ci) => (
              <li key={ci} className="space-y-1 rounded border border-white/5 p-2">
                <div className="flex gap-1">
                  <input className={`${field} font-semibold`} value={c.title} aria-label={t("outline_chapter_title")} onChange={(e) => setDraft(renameChapter(draft, ci, e.target.value))} />
                  <button title={t("outline_remove")} onClick={() => setDraft(removeChapter(draft, ci))} className="text-zinc-500 hover:text-red-300"><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
                {c.scenes.map((s, si) => (
                  <div key={si} className="ml-2 space-y-0.5 border-l border-white/10 pl-2">
                    <div className="flex gap-1">
                      <input className={field} value={s.title} aria-label={t("outline_scene_title")} onChange={(e) => setDraft(editScene(draft, ci, si, { title: e.target.value }))} />
                      <button title={t("outline_remove")} onClick={() => setDraft(removeScene(draft, ci, si))} className="text-zinc-500 hover:text-red-300"><Trash2 className="h-3 w-3" /></button>
                    </div>
                    <textarea className={`${field} min-h-[44px]`} value={s.summary} aria-label={t("scene_summary")} onChange={(e) => setDraft(editScene(draft, ci, si, { summary: e.target.value }))} />
                  </div>
                ))}
              </li>
            ))}
          </ol>
          {draft.entities.length > 0 && <p className="text-[11px] text-zinc-500">{t("outline_entities", { names: draft.entities.map((e) => e.name).join(", ") })}</p>}
          {problem && <p className="text-xs text-amber-200">{t(problem)}</p>}
          <div className="flex gap-2">
            <button onClick={() => { void apply() }} disabled={busy || !!problem}
              className="inline-flex flex-1 items-center justify-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}{t("outline_apply")}
            </button>
            <button onClick={() => setDraft(null)} className="rounded-lg border border-white/10 px-3 text-sm text-zinc-300">{t("ghost_reject")}</button>
          </div>
        </div>
      )}
      {error && <p className="st-ai-error rounded border border-red-400/30 bg-red-500/10 px-2 py-1 text-xs text-red-200" role="alert">{error}</p>}
    </section>
  )
}
