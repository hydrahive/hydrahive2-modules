import { useState } from "react"
import { Trash2 } from "lucide-react"
import { caseApi, type Party } from "./api"
import { errorText, PARTY_ROLES, partyRoleLabel } from "./caseFormat"

const input = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2 py-1 text-sm text-[#e8eef8]"

/** Reiter „Beteiligte“. */
export function PartyPanel({ pid, parties, canWrite, onChange }: { pid: string; parties: Party[]; canWrite: boolean; onChange: () => void }) {
  const [f, setF] = useState({ role: "opponent", name: "", address: "", contact: "", note: "" })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF((o) => ({ ...o, [k]: e.target.value }))

  async function add(e: React.FormEvent) {
    e.preventDefault()
    if (!f.name.trim()) { setError("Bitte einen Namen angeben."); return }
    setError(null)
    try { await caseApi.addParty(pid, { ...f, name: f.name.trim() }); setF((o) => ({ ...o, name: "", address: "", contact: "", note: "" })); onChange() }
    catch (err) { setError(errorText(err)) }
  }
  async function remove(p: Party) {
    if (!window.confirm(`„${p.name}“ aus der Akte entfernen?`)) return
    try { await caseApi.deleteParty(pid, p.id); onChange() } catch (err) { setError(errorText(err)) }
  }

  return (
    <div className="space-y-3">
      {parties.length === 0 && <p className="text-sm text-[#9aa7bc]">Noch keine Beteiligten.</p>}
      <ul className="space-y-1">
        {parties.map((p) => (
          <li key={p.id} className="flex items-start gap-2 rounded-[4px] border border-[rgb(var(--hh-s-rand,29_38_54))] p-2 text-sm">
            <div className="flex-1">
              <p className="text-[#e8eef8]"><b>{p.name}</b> <span className="text-xs text-[#9aa7bc]">({partyRoleLabel(p.role)})</span></p>
              {(p.address || p.contact) && <p className="text-xs text-[#9aa7bc]">{[p.address, p.contact].filter(Boolean).join(" · ")}</p>}
              {p.note && <p className="text-xs text-[#9aa7bc]">{p.note}</p>}
            </div>
            {canWrite && <button type="button" title="Entfernen" onClick={() => void remove(p)} className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-1 text-rose-300 hover:bg-[rgb(var(--hh-s-hebung,23_33_51))]"><Trash2 size={12} /></button>}
          </li>
        ))}
      </ul>
      {canWrite && (
        <form onSubmit={(e) => void add(e)} className="flex flex-wrap items-end gap-2 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-3 text-xs text-[#d7deea]">
          <label className="flex flex-col">Rolle
            <select value={f.role} onChange={set("role")} className={input}>{Object.entries(PARTY_ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          </label>
          <label className="flex flex-col">Name *<input value={f.name} onChange={set("name")} maxLength={200} className={input} /></label>
          <label className="flex flex-col">Anschrift<input value={f.address} onChange={set("address")} maxLength={500} className={input} /></label>
          <label className="flex flex-col">Kontakt<input value={f.contact} onChange={set("contact")} maxLength={300} className={input} /></label>
          <button type="submit" className="rounded-[4px] bg-[#1d4ed8] px-3 py-1 text-sm text-white">Hinzufügen</button>
          {error && <p className="w-full text-rose-300">{error}</p>}
        </form>
      )}
    </div>
  )
}
