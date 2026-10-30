import { useState } from "react"
import { Inbox, PenLine, Send, Trash2 } from "lucide-react"
import { letterApi, type Entry, type Party } from "./api"
import { errorText } from "./caseFormat"
import { DELIVERY_LABEL, entryLabel } from "./letterFormat"
import { LetterEditor } from "./LetterEditor"

const input = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2 py-1 text-sm text-[#e8eef8]"
type Mode = { kind: "list" } | { kind: "edit"; entry: Entry | null } | { kind: "in" } | { kind: "sent"; entry: Entry }

/** Reiter „Schriftverkehr“: Liste ein/aus, „Neuer Brief“, „Eingang erfassen“ (abschreiben/Kurzfassung bis L5),
 * „Versendet am … per …“. Kein automatischer Versand. */
export function CorrespondencePanel({ pid, entries, parties, canWrite, onChange }: {
  pid: string; entries: Entry[]; parties: Party[]; canWrite: boolean; onChange: () => void
}) {
  const [mode, setMode] = useState<Mode>({ kind: "list" })
  const [f, setF] = useState({ date: new Date().toISOString().slice(0, 10), sender: "", subject: "", body: "", delivery: "einwurf_einschreiben", proof: "" })
  const [error, setError] = useState<string | null>(null)
  const done = () => { setMode({ kind: "list" }); setError(null); onChange() }

  if (mode.kind === "edit") {
    return <LetterEditor pid={pid} parties={parties} entry={mode.entry} canWrite={canWrite} onSaved={done} onClose={() => setMode({ kind: "list" })} />
  }
  async function saveIncoming() {
    try { await letterApi.add(pid, { direction: "in", date: f.date, sender: f.sender, subject: f.subject, body: f.body }); done() }
    catch (e) { setError(errorText(e)) }
  }
  async function saveSent(entry: Entry) {
    try { await letterApi.sent(pid, entry.id, { date: f.date, delivery: f.delivery, proof: f.proof }); done() }
    catch (e) { setError(errorText(e)) }
  }
  async function remove(e: Entry) {
    if (!window.confirm(`„${e.subject || "ohne Betreff"}“ löschen?`)) return
    try { await letterApi.remove(pid, e.id); onChange() } catch (err) { setError(errorText(err)) }
  }

  return (
    <div className="space-y-3">
      {canWrite && mode.kind === "list" && (
        <div className="flex gap-2">
          <button type="button" onClick={() => setMode({ kind: "edit", entry: null })} className="inline-flex items-center gap-1 rounded-[4px] bg-[#1d4ed8] px-3 py-1 text-sm text-white"><PenLine size={13} />Neuer Brief</button>
          <button type="button" onClick={() => setMode({ kind: "in" })} className="inline-flex items-center gap-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1 text-sm text-[#d7deea]"><Inbox size={13} />Eingang erfassen</button>
        </div>
      )}
      {mode.kind === "in" && (
        <div className="space-y-2 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-3 text-xs text-[#d7deea]">
          <p className="text-[#9aa7bc]">Eingegangenes Schreiben abtippen oder kurz zusammenfassen. Hochladen kommt später (L5).</p>
          <div className="flex flex-wrap gap-2">
            <label className="flex flex-col">Eingang am<input type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} className={input} /></label>
            <label className="flex flex-1 flex-col">Absender<input value={f.sender} onChange={(e) => setF({ ...f, sender: e.target.value })} maxLength={500} className={input} /></label>
          </div>
          <input value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} placeholder="Betreff" maxLength={300} className={`${input} w-full`} />
          <textarea value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} placeholder="Inhalt / Kurzfassung" rows={5} className={`${input} w-full`} />
          <div className="flex gap-2"><button type="button" onClick={() => void saveIncoming()} className="rounded-[4px] bg-[#1d4ed8] px-3 py-1 text-sm text-white">Speichern</button>
            <button type="button" onClick={() => setMode({ kind: "list" })} className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1 text-sm">Abbrechen</button></div>
        </div>
      )}
      {error && <p className="text-xs text-rose-300">{error}</p>}
      {entries.length === 0 && mode.kind === "list" && <p className="text-sm text-[#9aa7bc]">Noch kein Schriftverkehr.</p>}
      <ul className="space-y-1">
        {entries.map((e) => (
          <li key={e.id} className="rounded-[4px] border border-[rgb(var(--hh-s-rand,29_38_54))] p-2">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <button type="button" onClick={() => setMode({ kind: "edit", entry: e })} className="font-semibold text-[#e8eef8] hover:underline" disabled={e.direction === "in"}>
                {e.subject || "(ohne Betreff)"}
              </button>
              <span className="text-xs text-[#9aa7bc]">{entryLabel(e)}{e.proof ? ` · Nachweis ${e.proof}` : ""}</span>
              {canWrite && (
                <span className="ml-auto flex gap-1">
                  {e.direction === "out" && e.status === "draft" && (
                    <button type="button" onClick={() => setMode({ kind: "sent", entry: e })} className="inline-flex items-center gap-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-0.5 text-xs text-emerald-300"><Send size={12} />versendet …</button>
                  )}
                  {e.status !== "sent" && <button type="button" title="Löschen" onClick={() => void remove(e)} className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-1 text-rose-300"><Trash2 size={12} /></button>}
                </span>
              )}
            </div>
            {e.direction === "in" && e.body && <p className="mt-1 whitespace-pre-wrap text-xs text-[#9aa7bc]">{e.body}</p>}
            {mode.kind === "sent" && mode.entry.id === e.id && (
              <div className="mt-2 flex flex-wrap items-end gap-2 text-xs text-[#d7deea]">
                <label className="flex flex-col">Versendet am<input type="date" value={f.date} onChange={(ev) => setF({ ...f, date: ev.target.value })} className={input} /></label>
                <label className="flex flex-col">per<select value={f.delivery} onChange={(ev) => setF({ ...f, delivery: ev.target.value })} className={input}>
                  {Object.entries(DELIVERY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
                <label className="flex flex-col">Nachweis (z. B. Sendungsnummer)<input value={f.proof} onChange={(ev) => setF({ ...f, proof: ev.target.value })} maxLength={200} className={input} /></label>
                <button type="button" onClick={() => void saveSent(e)} className="rounded-[4px] bg-emerald-700 px-3 py-1 text-sm text-white">Eintragen</button>
                <span className="w-full text-[#9aa7bc]">Danach ist der Brief gesperrt (Beweisstand). Es wird nichts verschickt – das machst du selbst.</span>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
