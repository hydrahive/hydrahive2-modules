// Ghostwriter G4d – Gliederungs-Vorschlag des Agenten im Modus „Kapitel/Buch“: ansehen, bearbeiten, übernehmen
// (Kapitel werden am Ende angehängt; bei neuem Buch ersetzt er die leere Start-Szene) oder verwerfen.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Sparkles } from "lucide-react"
import { StoryApiError } from "../api"
import { chatApi, type OutlineProposal } from "../chatApi"
import type { Outline } from "../outlineModel"
import type { BookState } from "../useBook"
import { OutlineEditor } from "./OutlineEditor"

export function OutlineProposalBox({ state, proposal }: { state: BookState; proposal: OutlineProposal }) {
  const { t } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const [draft, setDraft] = useState<Outline>(proposal.outline)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const fail = (e: unknown) => setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e))

  const apply = async () => {
    setBusy(true); setError("")
    try {
      await state.flush()
      const r = await chatApi.acceptOutline(projectId, book.id, draft, state.structureVersion())
      state.adoptStructure(r.structure, Object.values(r.scenes))
      state.setOutlineProposal(null)
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const reject = async () => {
    setBusy(true); setError("")
    try { await chatApi.discardOutline(projectId, book.id); state.setOutlineProposal(null) } catch (e) { fail(e) } finally { setBusy(false) }
  }

  return (
    <section className="st-outline-proposal space-y-2 rounded-xl border border-violet-400/40 bg-violet-500/10 p-3">
      <p className="flex items-center gap-1.5 text-xs font-semibold text-violet-100"><Sparkles className="h-3.5 w-3.5 text-violet-300" />{t("outline_proposal_title")}</p>
      {proposal.note && <p className="text-xs text-violet-200/80">{t("proposal_note", { note: proposal.note })}</p>}
      <OutlineEditor draft={draft} setDraft={setDraft} busy={busy} canWrite={canWrite}
        onApply={() => { void apply() }} onReject={() => { void reject() }} />
      {error && <p className="text-xs text-red-200" role="alert">{error}</p>}
    </section>
  )
}
