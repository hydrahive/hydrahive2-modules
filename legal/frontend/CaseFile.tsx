import { useCallback, useEffect, useState } from "react"
import { ArrowLeft, MessagesSquare } from "lucide-react"
import { caseApi, type CaseSnapshot } from "./api"
import { CASE_STATUS, errorText } from "./caseFormat"
import { CaseChat } from "./CaseChat"
import { DeadlinePanel } from "./DeadlinePanel"
import { NotesPanel } from "./NotesPanel"
import { PartyPanel } from "./PartyPanel"
import { ProposalPanel } from "./ProposalPanel"

type Tab = "overview" | "parties" | "deadlines" | "notes" | "proposals"
const TABS: [Tab, string][] = [["overview", "Übersicht"], ["parties", "Beteiligte"], ["deadlines", "Fristen"], ["notes", "Notizen"], ["proposals", "Vorschläge"]]

function Field({ name, value }: { name: string; value: string }) {
  if (!value) return null
  return <div><p className="text-[11px] uppercase text-[#68758a]">{name}</p><p className="whitespace-pre-wrap text-sm text-[#e8eef8]">{value}</p></div>
}

/** Fallakte (Spec §4.3): Reiter Übersicht · Beteiligte · Fristen · Notizen · Vorschläge, Chat mit dem Rechts-Agenten. */
export function CaseFile({ pid, onBack }: { pid: string; onBack: () => void }) {
  const [snap, setSnap] = useState<CaseSnapshot | null>(null)
  const [tab, setTab] = useState<Tab>("overview")
  const [chat, setChat] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const load = useCallback(() => { caseApi.get(pid).then(setSnap).catch((e) => setError(errorText(e))) }, [pid])
  useEffect(load, [load])

  const canWrite = snap?.role === "write" || snap?.role === "admin"
  async function setStatus(status: "open" | "waiting" | "done") {
    try { await caseApi.patch(pid, { status }); load() } catch (e) { setError(errorText(e)) }
  }

  return (
    <div className="flex min-h-0 flex-1 gap-[10px]">
      <section className="min-h-0 flex-1 space-y-3 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#0d131d] p-3">
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={onBack} className="inline-flex items-center gap-1 text-xs text-[#69d7ff]"><ArrowLeft size={13} />Alle Fälle</button>
          {snap && <h2 className="text-lg font-bold text-[#e8eef8]">{snap.case.title}</h2>}
          {snap && <span className="text-xs text-[#8d9ab0]">{snap.case.area} · {snap.state_name}</span>}
          <span className="ml-auto flex items-center gap-2">
            {snap && canWrite && (
              <select value={snap.case.status} onChange={(e) => void setStatus(e.target.value as "open")}
                className="rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-1 text-xs text-[#e8eef8]">
                {Object.entries(CASE_STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            )}
            {canWrite && (
              <button type="button" onClick={() => setChat((v) => !v)}
                className="inline-flex items-center gap-1 rounded-[4px] bg-[#1d4ed8] px-3 py-1 text-xs text-white">
                <MessagesSquare size={13} />{chat ? "Chat schließen" : "Mit dem Rechts-Agenten sprechen"}
              </button>
            )}
          </span>
        </div>
        {error && <p className="text-xs text-rose-300">{error}</p>}
        <nav className="flex gap-2 border-b border-[#2a364b] text-sm">
          {TABS.map(([k, v]) => (
            <button key={k} type="button" onClick={() => setTab(k)}
              className={tab === k ? "border-b-2 border-[#69d7ff] px-2 pb-1 font-semibold text-[#e8eef8]" : "px-2 pb-1 text-[#8d9ab0]"}>
              {v}{k === "proposals" && snap?.open_proposals ? ` (${snap.open_proposals})` : ""}
            </button>
          ))}
        </nav>
        {snap && tab === "overview" && (
          <div className="space-y-3">
            <Field name="Kurz" value={snap.case.summary} />
            <Field name="Sachverhalt" value={snap.case.facts} />
            <Field name="Ziel" value={snap.case.goal} />
            <Field name="Aktenzeichen Gegenseite" value={snap.case.their_ref} />
            <Field name="Eigenes Zeichen" value={snap.case.our_ref} />
            {!snap.case.summary && !snap.case.facts && <p className="text-sm text-[#8d9ab0]">Noch kein Sachverhalt erfasst.</p>}
          </div>
        )}
        {snap && tab === "parties" && <PartyPanel pid={pid} parties={snap.parties} canWrite={canWrite} onChange={load} />}
        {snap && tab === "deadlines" && <DeadlinePanel pid={pid} deadlines={snap.deadlines} canWrite={canWrite} stateName={snap.state_name} onChange={load} />}
        {snap && tab === "notes" && <NotesPanel pid={pid} notes={snap.notes} canWrite={canWrite} onChange={load} />}
        {snap && tab === "proposals" && <ProposalPanel pid={pid} canWrite={canWrite} onChange={load} />}
      </section>
      {chat && <CaseChat pid={pid} onClose={() => { setChat(false); load() }} />}
    </div>
  )
}
