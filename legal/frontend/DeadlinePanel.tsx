import { useState } from "react"
import { Calculator, Check, Trash2 } from "lucide-react"
import { caseApi, type CalcResult, type Deadline } from "./api"
import { deadlineLight, dueText, errorText, KIND_LABEL } from "./caseFormat"
import { shortDate } from "./legalFormat"
import { Light } from "./Light"

const input = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2 py-1 text-sm text-[#e8eef8]"

/** Rechenweg + Hinweise einer Frist (aus dem Backend, §§ 187/188/193 BGB). */
export function CalcSteps({ steps, warnings }: { steps: string[]; warnings: string[] }) {
  return (
    <div className="space-y-1 text-xs leading-5">
      <ol className="list-decimal space-y-0.5 pl-5 text-[#d7deea]">{steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
      {warnings.map((w, i) => <p key={i} className="text-amber-200/90">⚠ {w}</p>)}
    </div>
  )
}

/** Reiter „Fristen“: Liste mit Ampel, Rechner (rechnet erst vor, speichert auf Klick). */
export function DeadlinePanel({ pid, deadlines, canWrite, stateName, onChange }: {
  pid: string; deadlines: Deadline[]; canWrite: boolean; stateName: string; onChange: () => void
}) {
  const [f, setF] = useState({ label: "", event_date: "", kind: "weeks", amount: "2", start_rule: "event" })
  const [preview, setPreview] = useState<CalcResult | null>(null)
  const [open, setOpen] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setF((o) => ({ ...o, [k]: e.target.value })); setPreview(null)
  }
  const body = () => ({ event_date: f.event_date, kind: f.kind, amount: f.kind === "date" ? 0 : Number(f.amount), start_rule: f.start_rule })

  async function calc() {
    setError(null)
    try {
      const snap = await caseApi.get(pid)
      setPreview(await caseApi.calc({ ...body(), state: snap.case.state }))
    } catch (e) { setError(errorText(e)) }
  }
  async function save() {
    if (!f.label.trim()) { setError("Bitte angeben, wofür die Frist gilt."); return }
    setError(null)
    try { await caseApi.addDeadline(pid, { ...body(), label: f.label.trim() }); setPreview(null); setF((o) => ({ ...o, label: "" })); onChange() }
    catch (e) { setError(errorText(e)) }
  }
  const act = (p: Promise<unknown>) => { p.then(onChange).catch((e) => setError(errorText(e))) }

  return (
    <div className="space-y-4">
      {deadlines.length === 0 && <p className="text-sm text-[#9aa7bc]">Noch keine Fristen.</p>}
      <ul className="space-y-1">
        {deadlines.map((d) => (
          <li key={d.id} className="rounded-[4px] border border-[rgb(var(--hh-s-rand,29_38_54))] p-2">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <Light value={deadlineLight(d)} />
              <button type="button" onClick={() => setOpen(open === d.id ? null : d.id)} className="font-semibold text-[#e8eef8] hover:underline">
                {shortDate(d.due_date)}
              </button>
              <span className="text-[#d7deea]">{d.label}</span>
              <span className="text-xs text-[#9aa7bc]">
                {d.status === "open" ? dueText(d.due_date) : d.status === "done" ? "erledigt" : "versäumt"}
                {" · "}{d.kind === "date" ? "fester Tag" : `${d.amount} ${KIND_LABEL[d.kind]}`} ab {shortDate(d.event_date)}
              </span>
              {canWrite && (
                <span className="ml-auto flex gap-1">
                  {d.status === "open" && (
                    <button type="button" title="Als erledigt markieren" onClick={() => act(caseApi.setDeadlineStatus(pid, d.id, "done"))}
                      className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-1 text-emerald-300 hover:bg-[rgb(var(--hh-s-hebung,23_33_51))]"><Check size={12} /></button>
                  )}
                  <button type="button" title="Löschen" onClick={() => { if (window.confirm(`Frist „${d.label}“ löschen?`)) act(caseApi.deleteDeadline(pid, d.id)) }}
                    className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-1 text-rose-300 hover:bg-[rgb(var(--hh-s-hebung,23_33_51))]"><Trash2 size={12} /></button>
                </span>
              )}
            </div>
            {open === d.id && <div className="mt-2"><CalcSteps steps={d.calc.steps} warnings={d.calc.warnings} /></div>}
          </li>
        ))}
      </ul>
      {canWrite && (
        <div className="space-y-2 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-3">
          <h3 className="text-sm font-semibold text-[#e8eef8]">Frist rechnen ({stateName})</h3>
          <div className="flex flex-wrap items-end gap-2 text-xs text-[#d7deea]">
            <label className="flex flex-col">Wofür<input value={f.label} onChange={set("label")} maxLength={200} placeholder="z. B. Widerspruch Bescheid" className={input} /></label>
            <label className="flex flex-col">Ereignistag (Zugang)<input type="date" value={f.event_date} onChange={set("event_date")} className={input} /></label>
            <label className="flex flex-col">Art
              <select value={f.kind} onChange={set("kind")} className={input}>
                {Object.entries(KIND_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
            {f.kind !== "date" && <label className="flex flex-col">Anzahl<input type="number" min={1} value={f.amount} onChange={set("amount")} className={`${input} w-20`} /></label>}
            <label className="flex flex-col">Beginn
              <select value={f.start_rule} onChange={set("start_rule")} className={input}>
                <option value="event">Ereignis im Lauf des Tages (Normalfall)</option>
                <option value="day_start">Tagesbeginn zählt mit (§ 187 Abs. 2)</option>
              </select>
            </label>
            <button type="button" onClick={() => void calc()} disabled={!f.event_date}
              className="inline-flex items-center gap-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1 text-sm disabled:opacity-50"><Calculator size={13} />Rechnen</button>
          </div>
          {preview && (
            <div className="space-y-2 border-t border-[rgb(var(--hh-s-rand,42_54_75))] pt-2">
              <p className="text-sm text-[#e8eef8]">Fristende: <b>{preview.weekday}, {shortDate(preview.due_date)}</b></p>
              <CalcSteps steps={preview.steps} warnings={preview.warnings} />
              <button type="button" onClick={() => void save()} className="rounded-[4px] bg-[#1d4ed8] px-3 py-1 text-sm text-white">In die Akte übernehmen</button>
            </div>
          )}
          {error && <p className="text-xs text-rose-300">{error}</p>}
        </div>
      )}
    </div>
  )
}
