import { useState } from "react"
import { Trash2 } from "lucide-react"
import { caseApi, type CaseNote } from "./api"
import { errorText } from "./caseFormat"
import { shortDate } from "./legalFormat"

const input = "w-full rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2 py-1 text-sm text-[#e8eef8]"

/** Reiter „Notizen“: Recherche des Agenten (mit geprüften Normen) und eigene Notizen. */
export function NotesPanel({ pid, notes, canWrite, onChange }: { pid: string; notes: CaseNote[]; canWrite: boolean; onChange: () => void }) {
  const [f, setF] = useState({ title: "", body: "", citations: "" })
  const [error, setError] = useState<string | null>(null)

  async function add(e: React.FormEvent) {
    e.preventDefault()
    if (!f.title.trim() || !f.body.trim()) { setError("Titel und Text angeben."); return }
    setError(null)
    const citations = f.citations.split(/[;\n]/).map((c) => c.trim()).filter(Boolean)
    try { await caseApi.addNote(pid, { title: f.title.trim(), body: f.body, citations }); setF({ title: "", body: "", citations: "" }); onChange() }
    catch (err) { setError(errorText(err)) }
  }
  async function remove(n: CaseNote) {
    if (!window.confirm(`Notiz „${n.title}“ löschen?`)) return
    try { await caseApi.deleteNote(pid, n.id); onChange() } catch (err) { setError(errorText(err)) }
  }

  return (
    <div className="space-y-3">
      {notes.length === 0 && <p className="text-sm text-[#9aa7bc]">Noch keine Notizen.</p>}
      {notes.map((n) => (
        <article key={n.id} className="space-y-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,29_38_54))] p-2">
          <header className="flex items-start gap-2">
            <div className="flex-1">
              <p className="text-sm font-semibold text-[#e8eef8]">{n.title}</p>
              <p className="text-[11px] text-[#9aa7bc]">{n.author === "agent" ? "Agent" : "Notiz"} · {n.author_name} · {shortDate(n.created_at)}</p>
            </div>
            {canWrite && <button type="button" title="Löschen" onClick={() => void remove(n)} className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-1 text-rose-300 hover:bg-[rgb(var(--hh-s-hebung,23_33_51))]"><Trash2 size={12} /></button>}
          </header>
          <p className="whitespace-pre-wrap text-sm leading-6 text-[#d7deea]">{n.body}</p>
          {n.citations.length > 0 && (
            <p className="flex flex-wrap gap-1 text-[11px]">
              {n.citations.map((c) => (
                <span key={c.citation} title={c.found ? "im Gesetzeskorpus gefunden" : "nicht im Korpus – prüfen!"}
                  className={`rounded-[3px] px-1.5 py-0.5 ${c.found ? "bg-emerald-900/50 text-emerald-200" : "bg-rose-900/50 text-rose-200"}`}>
                  {c.found ? "✓" : "?"} {c.citation}
                </span>
              ))}
            </p>
          )}
        </article>
      ))}
      {canWrite && (
        <form onSubmit={(e) => void add(e)} className="space-y-2 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-3 text-xs text-[#d7deea]">
          <input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} maxLength={200} placeholder="Titel" className={input} />
          <textarea value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} maxLength={20000} rows={3} placeholder="Text" className={input} />
          <input value={f.citations} onChange={(e) => setF({ ...f, citations: e.target.value })} placeholder="Normen, mit ; getrennt (z. B. § 536c BGB; § 536 BGB)" className={input} />
          <button type="submit" className="rounded-[4px] bg-[#1d4ed8] px-3 py-1 text-sm text-white">Notiz speichern</button>
          {error && <p className="text-rose-300">{error}</p>}
        </form>
      )}
    </div>
  )
}
