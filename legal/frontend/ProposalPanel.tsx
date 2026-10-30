import { useEffect, useState } from "react"
import { Check, X } from "lucide-react"
import { caseApi, type Proposal } from "./api"
import { errorText, partyRoleLabel } from "./caseFormat"
import { shortDate } from "./legalFormat"
import { CalcSteps } from "./DeadlinePanel"
import { CheckList } from "./CheckList"
import { deDate, type CheckResult } from "./letterFormat"

function Body({ p }: { p: Proposal }) {
  const v = p.payload as Record<string, unknown>
  if (p.kind === "party") {
    return <p className="text-sm text-[#e8eef8]"><b>{String(v.name)}</b> <span className="text-xs text-[#9aa7bc]">({partyRoleLabel(String(v.role))})</span>{v.address ? ` · ${String(v.address)}` : ""}</p>
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
  if (p.kind === "letter") {
    return (
      <div className="grid gap-2 lg:grid-cols-[1fr_260px]">
        <div className="space-y-1 text-sm text-[#e8eef8]">
          <p><b>{String(v.subject)}</b> <span className="text-xs text-[#9aa7bc]">· {deDate(String(v.date))}</span></p>
          <p className="whitespace-pre-wrap text-xs text-[#9aa7bc]">An: {String(v.recipient)}</p>
          <details><summary className="cursor-pointer text-xs text-[#69d7ff]">Text anzeigen</summary>
            <p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-[#d7deea]">{String(v.body)}</p></details>
        </div>
        <CheckList check={(v.check as CheckResult) ?? null} />
      </div>
    )
  }
  return <p className="whitespace-pre-wrap text-sm text-[#e8eef8]">{String(v.text)}</p>
}

const KIND: Record<Proposal["kind"], string> = { party: "Beteiligter", deadline: "Frist", fact: "Tatsache", letter: "Brief (→ Schriftverkehr als Entwurf)" }

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
      <p className="text-xs text-[#9aa7bc]">Der Rechts-Agent ändert die Akte nie selbst. Prüfe jeden Vorschlag, bevor du ihn übernimmst.</p>
      {error && <p className="text-xs text-rose-300">{error}</p>}
      {list && list.length === 0 && <p className="text-sm text-[#9aa7bc]">Keine offenen Vorschläge.</p>}
      {list?.map((p) => (
        <div key={p.id} className="space-y-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-2">
          <p className="text-[11px] uppercase text-[#9aa7bc]">{KIND[p.kind]} · {p.author_name} · {shortDate(p.created_at)}</p>
          <Body p={p} />
          {canWrite && (
            <div className="flex gap-2 pt-1">
              <button type="button" onClick={() => void decide(p.id, true)} className="inline-flex items-center gap-1 rounded-[4px] bg-emerald-700 px-2 py-0.5 text-xs text-white"><Check size={12} />Übernehmen</button>
              <button type="button" onClick={() => void decide(p.id, false)} className="inline-flex items-center gap-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-0.5 text-xs text-[#d7deea]"><X size={12} />Verwerfen</button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
