// Ghostwriter G4c – Reiter „Steckbrief“: Vorschlag des Agenten (neuer Steckbrief oder Änderung), alt → neu je Feld.
// Übernehmen: eigene Änderungen vorher speichern, Versionsprüfung der Struktur, danach Struktur vom Server übernehmen.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Check, Loader2, Sparkles, X } from "lucide-react"
import { StoryApiError } from "../api"
import { groupLabelKey } from "../bookFactory"
import { chatApi } from "../chatApi"
import { entityRows, type EntityChangeKey, type EntityProposal } from "../entityProposal"
import type { Entity } from "../model"
import type { BookState } from "../useBook"

const LABEL: Record<EntityChangeKey, string> = { name: "entity_name", aliases: "entity_aliases", description: "entity_desc", fields: "entity_fields" }

interface Props { state: BookState; proposal: EntityProposal; current?: Entity; onDone: (entityId: string | null) => void }

export function EntityProposalBox({ state, proposal, current, onDone }: Props) {
  const { t } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const fail = (e: unknown) => setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e))
  const isNew = !proposal.entity_id

  const accept = async () => {
    setBusy(true); setError("")
    try {
      await state.flush()   // eigene Änderungen an Gliederung/Steckbriefen zuerst (sonst Versionskonflikt)
      const before = new Set(state.book.entities.map((e) => e.id))
      const st = await chatApi.acceptEntity(projectId, book.id, proposal.id, state.structureVersion())
      state.adoptStructure(st)
      state.clearEntityProposal(proposal.id)
      onDone(isNew ? (st.entities.find((e) => !before.has(e.id))?.id ?? null) : proposal.entity_id)
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const discard = async () => {
    setBusy(true); setError("")
    try { await chatApi.discardEntity(projectId, book.id, proposal.id); state.clearEntityProposal(proposal.id); onDone(isNew ? null : proposal.entity_id) }
    catch (e) { fail(e) } finally { setBusy(false) }
  }

  return (
    <section className="st-entity-proposal space-y-2 rounded-lg border border-[#69d7ff]/40 bg-[#69d7ff]/10 p-2.5 text-sm text-[#c8f2ff]">
      <p className="flex items-center gap-1.5 text-xs font-semibold">
        <Sparkles className="h-3.5 w-3.5 text-[#69d7ff]" />{t(isNew ? "entity_proposal_new" : "entity_proposal_change", { group: t(groupLabelKey(book.kind, proposal.kind)) })}
      </p>
      {proposal.note && <p className="text-xs text-[#69d7ff]">{t("proposal_note", { note: proposal.note })}</p>}
      <ul className="space-y-2">
        {entityRows(proposal, current).map((r) => (
          <li key={r.key} className="space-y-0.5">
            <p className="text-xs text-[#c8d2df]">{t(LABEL[r.key])}</p>
            {!isNew && <p className="st-entity-old whitespace-pre-wrap text-xs text-[#9aa7bc] line-through">{r.old || "–"}</p>}
            <p className="st-entity-new whitespace-pre-wrap text-xs text-[#e8eef8]">{r.proposed || "–"}</p>
          </li>
        ))}
      </ul>
      {canWrite && (
        <div className="flex flex-wrap gap-2">
          <button onClick={() => { void accept() }} disabled={busy}
            className="inline-flex items-center gap-1 rounded bg-emerald-600 px-2 py-0.5 text-xs font-semibold text-white disabled:opacity-40">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}{t(isNew ? "entity_proposal_create" : "entity_proposal_apply")}
          </button>
          <button onClick={() => { void discard() }} disabled={busy} className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">
            <X className="h-3.5 w-3.5" />{t("ghost_reject")}
          </button>
        </div>
      )}
      {error && <p className="text-xs text-red-200" role="alert">{error}</p>}
    </section>
  )
}
