import { useEffect, useRef, useState } from "react"
import { Printer, Save } from "lucide-react"
import { letterApi, type Entry, type Letter, type Party } from "./api"
import { errorText } from "./caseFormat"
import { CheckList } from "./CheckList"
import { DELIVERY_LABEL, type CheckResult } from "./letterFormat"
import { LetterPrint } from "./LetterPrint"

const input = "w-full rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2 py-1 text-sm text-[#e8eef8]"
const EMPTY: Letter = { letter_type: "", sender: "", recipient: "", date: "", their_ref: "", our_ref: "", subject: "", body: "",
                        delivery: "einwurf_einschreiben", attachments: [] }

/** Brief-Editor: Vorlage → Gerüst aus der Akte, Text bearbeiten, Prüfliste live (verzögert), als Entwurf speichern,
 * Druckansicht. Ein versendeter Brief ist nur noch lesbar (Beweisstand). */
export function LetterEditor({ pid, parties, entry, canWrite, onSaved, onClose }: {
  pid: string; parties: Party[]; entry: Entry | null; canWrite: boolean; onSaved: (e: Entry) => void; onClose: () => void
}) {
  const [l, setL] = useState<Letter>(entry ?? EMPTY)
  const [templates, setTemplates] = useState<{ key: string; label: string; hint: string }[]>([])
  const [tpl, setTpl] = useState("mangelanzeige")
  const [rid, setRid] = useState<number | "">(parties.find((p) => p.role === "opponent")?.id ?? "")
  const [check, setCheck] = useState<CheckResult | null>(null)
  const [print, setPrint] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const locked = !canWrite || entry?.status === "sent"

  useEffect(() => { letterApi.templates().then((r) => setTemplates(r.templates)).catch(() => {}) }, [])
  useEffect(() => {
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => { letterApi.check(pid, l).then(setCheck).catch(() => setCheck(null)) }, 600)
    return () => window.clearTimeout(timer.current)
  }, [pid, l])

  const set = (k: keyof Letter) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setL((o) => ({ ...o, [k]: e.target.value }))
  async function fromTemplate() {
    if (l.body.trim() && !window.confirm("Text durch das Gerüst der Vorlage ersetzen?")) return
    try { setL(await letterApi.draft(pid, tpl, rid === "" ? undefined : rid)); setError(null) } catch (e) { setError(errorText(e)) }
  }
  async function save() {
    setError(null)
    try { onSaved(entry ? await letterApi.update(pid, entry.id, l) : await letterApi.add(pid, { ...l, direction: "out" })) }
    catch (e) { setError(errorText(e)) }
  }

  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_300px]">
      <div className="space-y-2">
        {!entry && canWrite && (
          <div className="flex flex-wrap items-end gap-2 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-2 text-xs text-[#d7deea]">
            <label className="flex flex-col">Vorlage
              <select value={tpl} onChange={(e) => setTpl(e.target.value)} className={input}>
                {templates.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
              </select>
            </label>
            <label className="flex flex-col">Empfänger
              <select value={rid} onChange={(e) => setRid(e.target.value ? Number(e.target.value) : "")} className={input}>
                <option value="">– später eintragen –</option>
                {parties.filter((p) => p.role !== "me").map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
            <button type="button" onClick={() => void fromTemplate()} className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1 text-sm">Gerüst einsetzen</button>
            <span className="w-full text-[#9aa7bc]">{templates.find((t) => t.key === tpl)?.hint}</span>
          </div>
        )}
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="text-xs text-[#d7deea]">Absender<textarea value={l.sender} onChange={set("sender")} rows={3} className={input} disabled={locked} /></label>
          <label className="text-xs text-[#d7deea]">Empfänger<textarea value={l.recipient} onChange={set("recipient")} rows={3} className={input} disabled={locked} /></label>
          <label className="text-xs text-[#d7deea]">Datum<input type="date" value={l.date} onChange={set("date")} className={input} disabled={locked} /></label>
          <label className="text-xs text-[#d7deea]">Zustellweg
            <select value={l.delivery} onChange={set("delivery")} className={input} disabled={locked}>
              <option value="">– wählen –</option>
              {Object.entries(DELIVERY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="text-xs text-[#d7deea]">Ihr Zeichen<input value={l.their_ref} onChange={set("their_ref")} maxLength={100} className={input} disabled={locked} /></label>
          <label className="text-xs text-[#d7deea]">Unser Zeichen<input value={l.our_ref} onChange={set("our_ref")} maxLength={100} className={input} disabled={locked} /></label>
        </div>
        <label className="block text-xs text-[#d7deea]">Betreff<input value={l.subject} onChange={set("subject")} maxLength={300} className={input} disabled={locked} /></label>
        <label className="block text-xs text-[#d7deea]">Text<textarea value={l.body} onChange={set("body")} rows={16} className={`${input} font-mono`} disabled={locked} /></label>
        <label className="block text-xs text-[#d7deea]">Anlagen (je Zeile eine)
          <textarea value={l.attachments.join("\n")} rows={2} className={input} disabled={locked}
            onChange={(e) => setL((o) => ({ ...o, attachments: e.target.value.split("\n").filter((x) => x.trim()) }))} />
        </label>
        {error && <p className="text-xs text-rose-300">{error}</p>}
        <div className="flex flex-wrap gap-2">
          {!locked && <button type="button" onClick={() => void save()} className="inline-flex items-center gap-1 rounded-[4px] bg-[#1d4ed8] px-3 py-1 text-sm text-white"><Save size={13} />Als Entwurf speichern</button>}
          <button type="button" onClick={() => setPrint(true)} className="inline-flex items-center gap-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1 text-sm text-[#d7deea]"><Printer size={13} />Druckansicht</button>
          <button type="button" onClick={onClose} className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1 text-sm text-[#9aa7bc]">Schließen</button>
        </div>
      </div>
      <aside className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-2"><h3 className="mb-1 text-sm font-semibold text-[#e8eef8]">Prüfliste</h3><CheckList check={check} /></aside>
      {print && <LetterPrint letter={l} onClose={() => setPrint(false)} />}
    </div>
  )
}
