// Ghostwriter G2 – Hinweis über dem Editor: „KI-Vorschlag liegt bereit“ (Spec §9.3); seit G4 auch vom Agenten im Chat. Ansehen, Übernehmen
// (Server legt vorher einen Schnappschuss an, Versionsprüfung) oder Verwerfen. Die Szene bleibt bis dahin unberührt.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Check, Eye, EyeOff, Loader2, Sparkles, X } from "lucide-react"
import { StoryApiError } from "../api"
import { runApi } from "../runApi"
import type { ProposalMark } from "../serverBook"
import type { BookState } from "../useBook"

interface Props { state: BookState; sceneId: string; mark: ProposalMark }

export function ProposalBanner({ state, sceneId, mark }: Props) {
  const { t } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const [text, setText] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const fail = (e: unknown) => setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e))

  const view = async () => {
    if (text !== null) { setText(null); return }
    try { setText((await runApi.proposal(projectId, book.id, sceneId)).text) } catch (e) { fail(e) }
  }
  const accept = async () => {
    setBusy(true); setError("")
    try {
      await state.flush()
      const version = state.sceneVersion(sceneId) ?? 0
      const scene = await runApi.acceptProposal(projectId, book.id, sceneId, version)
      state.adoptScene(scene)
      state.reloadText()
      state.clearProposal(sceneId)
      void state.refresh(sceneId)   // Schnappschuss-Liste neu
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const discard = async () => {
    setBusy(true); setError("")
    try { await runApi.discardProposal(projectId, book.id, sceneId); state.clearProposal(sceneId) } catch (e) { fail(e) } finally { setBusy(false) }
  }

  return (
    <div className="st-proposal-banner mx-auto mb-4 max-w-3xl space-y-2 rounded-lg border border-violet-400/40 bg-violet-500/10 px-3 py-2 text-sm text-violet-100">
      <div className="flex flex-wrap items-center gap-2">
        <Sparkles className="h-4 w-4 shrink-0 text-violet-300" />
        <span className="flex-1">{t(mark.source === "agent" ? "proposal_from_agent" : "proposal_ready", { words: mark.words })}</span>
        <button onClick={() => { void view() }} className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs hover:bg-white/10">
          {text === null ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}{t(text === null ? "proposal_view" : "proposal_hide")}
        </button>
        {canWrite && <>
          <button onClick={() => { void accept() }} disabled={busy} className="inline-flex items-center gap-1 rounded bg-emerald-600 px-2 py-0.5 text-xs font-semibold text-white disabled:opacity-40">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}{t("ghost_accept_replace")}
          </button>
          <button onClick={() => { void discard() }} disabled={busy} className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs hover:bg-white/10">
            <X className="h-3.5 w-3.5" />{t("ghost_reject")}
          </button>
        </>}
      </div>
      {mark.note && <p className="st-proposal-note text-xs text-violet-200/80">{t("proposal_note", { note: mark.note })}</p>}
      {text !== null && <div className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded bg-black/20 p-2 font-serif text-sm leading-relaxed text-zinc-200">{text}</div>}
      {error && <p className="text-xs text-red-200" role="alert">{error}</p>}
    </div>
  )
}
