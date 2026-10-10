// C2 – Umbau-Vorschlag des Autors im Modus „Kapitel/Buch“ (Spec autor-gliederung-c2.md §2b): Schritte in Klartext,
// Kapitel vorher → nachher, Übernehmen (erst speichern, dann der Server führt aus) oder Verwerfen (→ Verlauf).
// Passt der Vorschlag nicht mehr zur Gliederung, meldet der Server den Schritt – der Vorschlag bleibt.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { ListTree } from "lucide-react"
import { StoryApiError } from "../api"
import { originLabel } from "../proposalHistory"
import { chapterDiff, restructureApi, type RestructureProposal } from "../restructure"
import type { BookState } from "../useBook"

export function RestructureProposalBox({ state, proposal }: { state: BookState; proposal: RestructureProposal }) {
  const { t } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const fail = (e: unknown) => setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e))
  const diff = chapterDiff(proposal.before, proposal.after)

  const apply = async () => {
    setBusy(true); setError("")
    try {
      await state.flush()
      const r = await restructureApi.accept(projectId, book.id)
      state.adoptStructure(r.structure, r.scenes)
      state.setRestructureProposal(null)
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const reject = async () => {
    setBusy(true); setError("")
    try { await restructureApi.discard(projectId, book.id); state.setRestructureProposal(null) } catch (e) { fail(e) } finally { setBusy(false) }
  }

  return (
    <section className="st-restructure-proposal space-y-2 rounded-xl border border-violet-400/40 bg-violet-500/10 p-3 text-xs">
      <p className="flex items-center gap-1.5 font-semibold text-violet-100"><ListTree className="h-3.5 w-3.5 text-violet-300" />{t("struct_proposal_title")}</p>
      {proposal.note && <p className="text-violet-200/80">{t("proposal_note", { note: proposal.note })}</p>}
      {proposal.replaced_from && <p className="st-proposal-replaced text-violet-200/70">
        {t("struct_proposal_replaced", { who: originLabel({ author: proposal.replaced_from.author }, t) })}</p>}
      <div>
        <p className="mb-1 text-zinc-400">{t("struct_proposal_steps")}</p>
        <ol className="st-restructure-steps list-decimal space-y-0.5 pl-5 text-zinc-200">
          {proposal.lines.map((line, i) => <li key={i}>{line}</li>)}
        </ol>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="mb-1 text-zinc-400">{t("struct_proposal_before")}</p>
          <ul className="st-restructure-before space-y-0.5 text-zinc-400">
            {proposal.before.map((title, i) => <li key={i} className={diff.gone.includes(title) ? "line-through text-red-300/80" : ""}>{title}</li>)}
          </ul>
        </div>
        <div>
          <p className="mb-1 text-zinc-400">{t("struct_proposal_after")}</p>
          <ul className="st-restructure-after space-y-0.5 text-zinc-200">
            {diff.after.map((c, i) => (
              <li key={i}>{c.title}{c.kind === "new" && <span className="ml-1 rounded bg-emerald-500/15 px-1 text-[10px] text-emerald-300">{t("struct_proposal_new")}</span>}</li>
            ))}
          </ul>
        </div>
      </div>
      {canWrite && (
        <div className="flex gap-2">
          <button onClick={() => { void apply() }} disabled={busy}
            className="rounded-lg bg-violet-600 px-3 py-1.5 font-semibold text-white hover:bg-violet-500 disabled:opacity-40">{t("struct_apply")}</button>
          <button onClick={() => { void reject() }} disabled={busy}
            className="rounded-lg border border-white/10 px-3 py-1.5 text-zinc-300 hover:bg-white/5 disabled:opacity-40">{t("struct_reject")}</button>
        </div>
      )}
      {error && <p className="text-red-200" role="alert">{error}</p>}
    </section>
  )
}
