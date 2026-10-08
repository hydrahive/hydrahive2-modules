// A2 – Reiter „Szene“: frühere (ersetzte oder verworfene) Vorschläge dieser Szene. Ansehen, Zurückholen (wird wieder
// zum offenen Vorschlag; ein gerade offener wandert dafür in den Verlauf). Lädt erst beim Aufklappen.
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ChevronDown, ChevronRight, History } from "lucide-react"
import { StoryApiError } from "../api"
import { infoMarks } from "../infoProposal"
import { historyApi, originLabel, type HistoryEntry } from "../proposalHistory"
import { markOf } from "../proposalMark"
import type { BookState } from "../useBook"

interface Props { state: BookState; sceneId: string }

export function ProposalHistory({ state, sceneId }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<HistoryEntry[] | null>(null)
  const [shown, setShown] = useState<{ id: string; text: string } | null>(null)
  const [error, setError] = useState("")
  const fmt = (iso: string) => new Date(iso).toLocaleString(i18n.language, { dateStyle: "short", timeStyle: "short" })
  const fail = (e: unknown) => setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e))

  const load = useCallback(() => historyApi.list(projectId, book.id, sceneId).then(setRows), [projectId, book.id, sceneId])
  // Szene gewechselt oder offener Vorschlag geändert (ersetzt/verworfen) → Liste neu, sobald aufgeklappt.
  const marker = `${state.proposals[sceneId]?.at ?? ""}|${state.infoProposals[sceneId]?.at ?? ""}`
  useEffect(() => {
    if (!open) return
    load().catch(fail)
  }, [open, load, marker])   // eslint-disable-line react-hooks/exhaustive-deps

  const view = async (e: HistoryEntry) => {
    if (shown?.id === e.id) { setShown(null); return }
    if (e.kind !== "text") { setShown({ id: e.id, text: Object.entries(e.fields ?? {}).map(([k, v]) => `${t(`scene_${k}`)}: ${v}`).join("\n") }); return }
    try { setShown({ id: e.id, text: (await historyApi.get(projectId, book.id, sceneId, "text", e.id)).text ?? "" }) } catch (x) { fail(x) }
  }
  const restore = async (e: HistoryEntry) => {
    setError("")
    try {
      if (e.kind === "text") {
        const p = await historyApi.restore(projectId, book.id, sceneId, "text", e.id)
        state.markProposals({ [sceneId]: markOf(p) })
      } else {
        const p = await historyApi.restore(projectId, book.id, sceneId, "info", e.id)
        state.setInfoProposals((all) => ({ ...all, ...infoMarks([p]) }))
      }
      setShown(null)
      await load()
    } catch (x) { fail(x) }
  }

  return (
    <section className="st-proposal-history space-y-1">
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-xs font-semibold text-zinc-400 hover:text-zinc-200">
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        <History className="h-3.5 w-3.5" />{t("history_title")}{rows ? ` (${rows.length})` : ""}
      </button>
      {open && rows && rows.length === 0 && <p className="text-xs text-zinc-600">{t("history_none")}</p>}
      {open && rows && rows.length > 0 && (
        <ul className="space-y-1 text-xs">
          {rows.map((e) => (
            <li key={`${e.kind}-${e.id}`} className="st-history-entry space-y-1 rounded border border-white/5 px-2 py-1 text-zinc-400">
              <div className="flex flex-wrap items-center gap-x-2">
                <span className="text-zinc-300">{t(`history_kind_${e.kind}`)}</span>
                <span>{t("history_from", { who: originLabel(e, t) })}</span>
                <span className="text-zinc-500">{fmt(e.at)}</span>
                {e.kind === "text" && <span className="text-zinc-500">{t("history_words", { n: e.words ?? 0 })}</span>}
                <span className="text-zinc-500">· {e.reason === "discarded" ? t("history_discarded")
                  : e.reason === "restored_over" ? t("history_restored_over")
                  : t("history_replaced_by", { who: originLabel({ author: e.replaced_by }, t) })}</span>
                <span className="ml-auto flex gap-2">
                  <button onClick={() => { void view(e) }} className="text-violet-300 hover:underline">{t(shown?.id === e.id ? "proposal_hide" : "proposal_view")}</button>
                  {canWrite && <button onClick={() => { void restore(e) }} className="st-history-restore text-violet-300 hover:underline">{t("history_restore")}</button>}
                </span>
              </div>
              {shown?.id === e.id && <div className="max-h-56 overflow-y-auto whitespace-pre-wrap rounded bg-black/20 p-2 font-serif text-sm text-zinc-200">{shown.text}</div>}
            </li>
          ))}
        </ul>
      )}
      {error && <p className="text-xs text-red-300" role="alert">{error}</p>}
    </section>
  )
}
