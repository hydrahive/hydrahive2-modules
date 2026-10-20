import { useEffect, useState } from "react"
import { Check, X } from "lucide-react"
import { caseApi, type Proposal } from "./api"
import { errorText, partyRoleLabel } from "./caseFormat"
import { shortDate } from "./legalFormat"
import { CalcSteps } from "./DeadlinePanel"

function Body({ p }: { p: Proposal }) {
  const v = p.payload as Record<string, unknown>
  if (p.kind === "party") {
    return <p className="text-sm text-[#e8eef8]"><b>{String(v.name)}</b> <span className="text-xs text-[#8d9ab0]">({partyRoleLabel(String(v.role))})</span>{v.address ? ` · ${String(v.address)}` : ""}</p>
  }
  if (p.kind === "deadline") {
    const calc = v.calc as { steps: string[]; warnings: string[] }
    return (
      <div className="space-y-1">
        <p className="text-sm text-[#e8eef8]"><b>{String(v.label)}</b> – Fristende {shortDate(String(v.due_date))}</p>
        <CalcSteps steps={calc.steps} warnings={calc.warnings} />
      </div>
    )
  }
  return <p className="whitespace-pre-wrap text-sm text-[#e8eef8]">{String(v.text)}</p>
}

const KIND: Record<Proposal["kind"], string> = { party: "Beteiligter", deadline: "Frist", fact: "Tatsache" }

/** Reiter „Vorschläge“: was der Rechts-Agent ablegen möchte – erst nach „Übernehmen“ steht es in der Akte. */
export function ProposalPanel({ pid, canWrite, onChange }: { pid: string; canWrite: boolean; onChange: () => void }) {
  const [list, setList] = useState<Proposal[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = () => { caseApi.proposals(pid).then((r) => setList(r.proposals)).catch((e) => setError(errorText(e))) }
  useEffect(load, [pid])

  async function decide(id: number, accept: boolean) {
    setError(null)
    try { await caseApi.decide(pid, id, accept); load(); onChange() } catch (e) { setError(errorText(e)) }
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-[#8d9ab0]">Der Rechts-Agent ändert die Akte nie selbst. Prüfe jeden Vorschlag, bevor du ihn übernimmst.</p>
      {error && <p className="text-xs text-rose-300">{error}</p>}
      {list && list.length === 0 && <p className="text-sm text-[#8d9ab0]">Keine offenen Vorschläge.</p>}
      {list?.map((p) => (
        <div key={p.id} className="space-y-1 rounded-[4px] border border-[#2a364b] p-2">
          <p className="text-[11px] uppercase text-[#68758a]">{KIND[p.kind]} · {p.author_name} · {shortDate(p.created_at)}</p>
          <Body p={p} />
          {canWrite && (
            <div className="flex gap-2 pt-1">
              <button type="button" onClick={() => void decide(p.id, true)} className="inline-flex items-center gap-1 rounded-[4px] bg-emerald-700 px-2 py-0.5 text-xs text-white"><Check size={12} />Übernehmen</button>
              <button type="button" onClick={() => void decide(p.id, false)} className="inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-0.5 text-xs text-[#d7deea]"><X size={12} />Verwerfen</button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
