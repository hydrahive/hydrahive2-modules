import { useEffect, useState } from "react"
import { FolderOpen, Plus } from "lucide-react"
import { caseApi, type CaseListItem } from "./api"
import { CASE_STATUS, deadlineLight, dueText, errorText } from "./caseFormat"
import { shortDate } from "./legalFormat"
import { CaseNew } from "./CaseNew"
import { Light } from "./Light"

/** Reiter „Fälle“: eigene und Mitglieds-Fälle mit Ampel der nächsten Frist; „Neuer Fall“ öffnet das Aufnahmeformular. */
export function CaseList({ onOpen }: { onOpen: (pid: string) => void }) {
  const [cases, setCases] = useState<CaseListItem[] | null>(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () => { caseApi.list().then((r) => setCases(r.cases)).catch((e) => setError(errorText(e))) }
  useEffect(load, [])

  if (creating) {
    return <CaseNew onCancel={() => setCreating(false)} onCreated={(pid) => { setCreating(false); onOpen(pid) }} />
  }
  return (
    <section className="min-h-0 space-y-3 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#0d131d] p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-[#8d9ab0]">Jeder Fall ist ein eigenes Projekt mit Rechts-Agent. Mitglieder siehst du im Projekt.</p>
        <button type="button" onClick={() => setCreating(true)}
          className="inline-flex items-center gap-1 rounded-[4px] bg-[#1d4ed8] px-3 py-1.5 text-sm text-white">
          <Plus size={14} />Neuer Fall
        </button>
      </div>
      {error && <p className="text-xs text-rose-300">{error}</p>}
      {cases && cases.length === 0 && <p className="text-sm text-[#8d9ab0]">Noch keine Fälle.</p>}
      {cases && cases.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead className="text-[11px] uppercase text-[#68758a]">
            <tr><th className="py-1">Fall</th><th>Status</th><th>Nächste Frist</th><th>Geändert</th><th /></tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.project_id} className="border-t border-[#1d2636]">
                <td className="py-1.5">
                  <span className="font-semibold text-[#e8eef8]">{c.title}</span>
                  {c.area && <span className="ml-2 text-xs text-[#8d9ab0]">{c.area}</span>}
                </td>
                <td className="text-xs text-[#d7deea]">{CASE_STATUS[c.status] ?? c.status}</td>
                <td className="text-xs text-[#d7deea]">
                  {c.next_deadline ? (
                    <span className="inline-flex items-center gap-1.5">
                      <Light value={deadlineLight({ ...c.next_deadline, status: "open" })} />
                      {shortDate(c.next_deadline.due_date)} · {dueText(c.next_deadline.due_date)} · {c.next_deadline.label}
                    </span>
                  ) : <span className="text-[#68758a]">–</span>}
                </td>
                <td className="text-xs text-[#8d9ab0]">{shortDate(c.updated_at)}</td>
                <td className="text-right">
                  <button type="button" onClick={() => onOpen(c.project_id)}
                    className="inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-0.5 text-xs text-[#69d7ff] hover:bg-[#172133]">
                    <FolderOpen size={12} />Öffnen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
