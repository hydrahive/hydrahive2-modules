// Ghostwriter G4b – Reiter „Szene“: Vorschlag des Agenten für Titel/Zusammenfassung/Perspektive (Spec §11.5).
// Vergleich alt → neu je Feld, Häkchen je Feld, Übernehmen (vorher eigene Änderungen speichern, Versionsprüfung)
// oder Verwerfen. Die Szene bleibt bis dahin unberührt.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Check, Loader2, Sparkles, X } from "lucide-react"
import { StoryApiError } from "../api"
import { chatApi } from "../chatApi"
import { chosenFields, infoRows, type InfoField, type InfoProposal } from "../infoProposal"
import { originLabel } from "../proposalHistory"
import type { Scene } from "../model"
import type { BookState } from "../useBook"

interface Props { state: BookState; scene: Scene; proposal: InfoProposal }

export function InfoProposalBox({ state, scene, proposal }: Props) {
  const { t } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const [checked, setChecked] = useState<Partial<Record<InfoField, boolean>>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const rows = infoRows(proposal, scene)
  const chosen = chosenFields(rows, checked)
  const fail = (e: unknown) => setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e))
  const show = (f: InfoField, v: string) => (f === "pov" && !v ? t("scene_pov_none") : v || "–")

  const accept = async () => {
    setBusy(true); setError("")
    try {
      await state.flush()   // eigene, noch nicht gespeicherte Änderungen zuerst (sonst Versionskonflikt)
      const saved = await chatApi.acceptInfo(projectId, book.id, scene.id, state.sceneVersion(scene.id) ?? 0, chosen)
      state.adoptScene(saved)
      state.clearInfoProposal(scene.id)
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const discard = async () => {
    setBusy(true); setError("")
    try { await chatApi.discardInfo(projectId, book.id, scene.id); state.clearInfoProposal(scene.id) }
    catch (e) { fail(e) } finally { setBusy(false) }
  }

  return (
    <section className="st-info-proposal space-y-2 rounded-lg border border-violet-400/40 bg-violet-500/10 p-2.5 text-sm text-violet-100">
      <p className="flex items-center gap-1.5 text-xs font-semibold"><Sparkles className="h-3.5 w-3.5 text-violet-300" />{t("info_proposal_title")}</p>
      {proposal.author && <p className="text-xs text-violet-200/80">{t("history_from", { who: originLabel(proposal, t) })}</p>}
      {proposal.note && <p className="text-xs text-violet-200/80">{t("proposal_note", { note: proposal.note })}</p>}
      {proposal.replaced_from && <p className="st-proposal-replaced text-xs text-violet-200/80">
        {t("replaced_hint", { who: originLabel({ author: proposal.replaced_from.author }, t) })}</p>}
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.field} className="space-y-0.5">
            <label className="flex items-center gap-1.5 text-xs text-zinc-300">
              <input type="checkbox" disabled={!canWrite || r.same} checked={!r.same && checked[r.field] !== false}
                onChange={(e) => setChecked((c) => ({ ...c, [r.field]: e.target.checked }))} />
              {t(`scene_${r.field}`)}{r.same && <span className="text-zinc-500">· {t("info_proposal_same")}</span>}
            </label>
            <p className="st-info-old whitespace-pre-wrap text-xs text-zinc-500 line-through">{show(r.field, r.old)}</p>
            <p className="st-info-new whitespace-pre-wrap text-xs text-zinc-100">{show(r.field, r.proposed)}</p>
          </li>
        ))}
      </ul>
      {canWrite && (
        <div className="flex flex-wrap gap-2">
          <button onClick={() => { void accept() }} disabled={busy || chosen.length === 0}
            className="inline-flex items-center gap-1 rounded bg-emerald-600 px-2 py-0.5 text-xs font-semibold text-white disabled:opacity-40">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}{t("info_proposal_accept")}
          </button>
          <button onClick={() => { void discard() }} disabled={busy} className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs hover:bg-white/10">
            <X className="h-3.5 w-3.5" />{t("ghost_reject")}
          </button>
        </div>
      )}
      {error && <p className="text-xs text-red-200" role="alert">{error}</p>}
    </section>
  )
}
