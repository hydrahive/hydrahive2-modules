import { useEffect, useState } from "react"
import { caseApi } from "./api"
import { caseFormErrors, errorText, modelState } from "./caseFormat"
import { CaseModel } from "./CaseModel"
import { useModelCatalog } from "./useModelCatalog"

const input = "w-full rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-1.5 text-sm text-[#e8eef8]"
const label = "block text-xs font-semibold text-[#d7deea]"
const hint = "mt-0.5 block text-[11px] font-normal leading-4 text-[#68758a]"

/** Aufnahmeformular „Neuer Fall“ (Spec §4.3). Pflicht: Titel + Bundesland. Legt Projekt + Rechts-Agent an. */
export function CaseNew({ onCancel, onCreated }: { onCancel: () => void; onCreated: (pid: string) => void }) {
  const [states, setStates] = useState<Record<string, string>>({})
  const [f, setF] = useState({ title: "", area: "", state: "", summary: "", facts: "", goal: "", their_ref: "" })
  const [touched, setTouched] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const catalog = useModelCatalog()
  const [model, setModel] = useState("")

  useEffect(() => { caseApi.states().then((r) => setStates(r.states)).catch((e) => setError(errorText(e))) }, [])
  const errs = caseFormErrors(f, modelState(catalog, model))
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setF((o) => ({ ...o, [k]: e.target.value }))

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setTouched(true)
    if (Object.keys(errs).length) return
    setBusy(true); setError(null)
    try {
      const out = await caseApi.create({ ...f, title: f.title.trim(), ...(model ? { model } : {}) })
      onCreated(out.project_id)
    } catch (err) { setError(errorText(err)) } finally { setBusy(false) }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="min-h-0 max-w-3xl space-y-3 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#0d131d] p-4">
      <h2 className="text-lg font-bold text-[#e8eef8]">Neuer Fall</h2>
      <p className="text-xs leading-5 text-[#8d9ab0]">
        Der Fall wird ein eigenes Projekt mit einem Rechts-Agenten. Der Agent sucht Normen, rechnet Fristen und macht
        Vorschläge – er verschickt nichts und ändert die Akte nicht selbst. Felder mit * sind Pflicht, alles andere kannst du später ergänzen.
      </p>
      <label className={label}>Titel *<span className={hint}>Kurz, z. B. „Mietminderung Hitze 2026“.</span>
        <input value={f.title} onChange={set("title")} maxLength={200} className={input} aria-invalid={touched && !!errs.title} />
        {touched && errs.title && <span className="text-[11px] text-rose-300">{errs.title}</span>}
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className={label}>Rechtsgebiet<span className={hint}>Falls bekannt, z. B. Mietrecht, Arbeitsrecht.</span>
          <input value={f.area} onChange={set("area")} maxLength={100} className={input} />
        </label>
        <label className={label}>Bundesland *<span className={hint}>Wo die Frist zu wahren ist – entscheidet über Feiertage.</span>
          <select value={f.state} onChange={set("state")} className={input} aria-invalid={touched && !!errs.state}>
            <option value="">– wählen –</option>
            {Object.entries(states).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          {touched && errs.state && <span className="text-[11px] text-rose-300">{errs.state}</span>}
        </label>
      </div>
      <label className={label}>Was ist passiert? (kurz)<span className={hint}>Zwei, drei Sätze – steht auch in der Projektbeschreibung für den Agenten.</span>
        <textarea value={f.summary} onChange={set("summary")} maxLength={2000} rows={2} className={input} />
      </label>
      <label className={label}>Sachverhalt im Detail<span className={hint}>Seit wann, wer ist beteiligt, was wurde schon getan (mit Datum).</span>
        <textarea value={f.facts} onChange={set("facts")} maxLength={20000} rows={6} className={input} />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className={label}>Was willst du erreichen?
          <textarea value={f.goal} onChange={set("goal")} maxLength={2000} rows={2} className={input} />
        </label>
        <label className={label}>Aktenzeichen der Gegenseite<span className={hint}>Falls vorhanden (Behörde, Gericht, Anwalt).</span>
          <input value={f.their_ref} onChange={set("their_ref")} maxLength={100} className={input} />
        </label>
      </div>
      <CaseModel catalog={catalog} value={model} onChange={setModel} error={touched ? errs.model : undefined} />
      <p className="text-[11px] leading-4 text-[#68758a]">Bekannte Fristen trägst du danach in der Fallakte unter „Fristen“ ein – dort wird mit Rechenweg gerechnet.</p>
      {error && <p className="text-xs text-rose-300">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={busy} className="rounded-[4px] bg-[#1d4ed8] px-3 py-1.5 text-sm text-white disabled:opacity-50">
          {busy ? "Lege an …" : "Fall anlegen"}
        </button>
        <button type="button" onClick={onCancel} className="rounded-[4px] border border-[#2a364b] px-3 py-1.5 text-sm text-[#d7deea]">Abbrechen</button>
      </div>
    </form>
  )
}
