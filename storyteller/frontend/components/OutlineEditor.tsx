// Gliederung vor dem Übernehmen bearbeiten (Kapitel/Szenen umbenennen, Zusammenfassung, streichen) – gemeinsam für
// „Gliederung aus Idee“ (G2) und den Gliederungs-Vorschlag des Agenten (G4d). Übernehmen/Verwerfen macht der Aufrufer.
import { useTranslation } from "react-i18next"
import { Check, Loader2, Trash2 } from "lucide-react"
import { editScene, outlineProblem, outlineStats, removeChapter, removeScene, renameChapter, type Outline } from "../outlineModel"

const field = "w-full rounded border border-white/10 bg-zinc-950 px-2 py-1 text-xs text-zinc-100"

interface Props {
  draft: Outline
  setDraft: (o: Outline) => void
  busy: boolean
  canWrite: boolean
  onApply: () => void
  onReject: () => void
}

export function OutlineEditor({ draft, setDraft, busy, canWrite, onApply, onReject }: Props) {
  const { t } = useTranslation("storyteller")
  const problem = outlineProblem(draft)
  return (
    <div className="space-y-2">
      <p className="text-xs text-zinc-400">{t("outline_review", outlineStats(draft))}</p>
      <ol className="max-h-96 space-y-2 overflow-y-auto pr-1">
        {draft.chapters.map((c, ci) => (
          <li key={ci} className="space-y-1 rounded border border-white/5 p-2">
            <div className="flex gap-1">
              <input className={`${field} font-semibold`} value={c.title} aria-label={t("outline_chapter_title")} readOnly={!canWrite}
                onChange={(e) => setDraft(renameChapter(draft, ci, e.target.value))} />
              {canWrite && <button title={t("outline_remove")} onClick={() => setDraft(removeChapter(draft, ci))} className="text-zinc-500 hover:text-red-300"><Trash2 className="h-3.5 w-3.5" /></button>}
            </div>
            {c.scenes.map((s, si) => (
              <div key={si} className="ml-2 space-y-0.5 border-l border-white/10 pl-2">
                <div className="flex gap-1">
                  <input className={field} value={s.title} aria-label={t("outline_scene_title")} readOnly={!canWrite}
                    onChange={(e) => setDraft(editScene(draft, ci, si, { title: e.target.value }))} />
                  {canWrite && <button title={t("outline_remove")} onClick={() => setDraft(removeScene(draft, ci, si))} className="text-zinc-500 hover:text-red-300"><Trash2 className="h-3 w-3" /></button>}
                </div>
                <textarea className={`${field} min-h-[44px] max-h-40 [field-sizing:content]`} value={s.summary} aria-label={t("scene_summary")} readOnly={!canWrite}
                  onChange={(e) => setDraft(editScene(draft, ci, si, { summary: e.target.value }))} />
              </div>
            ))}
          </li>
        ))}
      </ol>
      {draft.entities.length > 0 && <p className="text-[11px] text-zinc-500">{t("outline_entities", { names: draft.entities.map((e) => e.name).join(", ") })}</p>}
      {problem && <p className="text-xs text-amber-200">{t(problem)}</p>}
      {canWrite && (
        <div className="flex gap-2">
          <button onClick={onApply} disabled={busy || !!problem}
            className="inline-flex flex-1 items-center justify-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}{t("outline_apply")}
          </button>
          <button onClick={onReject} disabled={busy} className="rounded-lg border border-white/10 px-3 text-sm text-zinc-300">{t("ghost_reject")}</button>
        </div>
      )}
    </div>
  )
}
