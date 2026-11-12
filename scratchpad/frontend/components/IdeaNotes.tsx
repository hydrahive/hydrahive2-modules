import { Trash2 } from "lucide-react"
import { formatStamp } from "../ideaView"
import type { T } from "../texts.de"
import type { IdeaNote } from "../types"

interface Props {
  notes: IdeaNote[]
  locale: string
  t: T
  onRemove: (noteId: number) => void
}

/** Anmerkungen der Agenten neben der Idee. Als reiner Text ausgegeben, einzeln löschbar. */
export function IdeaNotes({ notes, locale, t, onRemove }: Props) {
  return (
    <section aria-labelledby="idea-notes-title" className="space-y-2">
      <div>
        <h3 id="idea-notes-title" className="text-sm font-bold text-[#e8eef8]">{t("notes_title")}</h3>
        <p className="mt-0.5 text-[11px] text-[#9aa7bc]">{t("notes_hint")}</p>
      </div>
      {notes.length === 0 ? (
        <p className="text-xs text-[#9aa7bc]">{t("notes_empty")}</p>
      ) : (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li key={note.id} className="rounded-[6px] border border-[rgb(var(--hh-s-rand,52_66_92))] bg-[rgb(var(--hh-s-tief,14_20_31))] px-3 py-2">
              <div className="flex items-center gap-2 text-[11px] text-[#9aa7bc]">
                <span className="font-semibold text-[#c8d2df]">{note.agent_name || t(note.author === "agent" ? "note_author_agent" : "note_author_system")}</span>
                <span>{formatStamp(note.created_at, locale)}</span>
                <button type="button" onClick={() => onRemove(note.id)} aria-label={t("note_delete")} title={t("note_delete")}
                  className="ml-auto grid h-6 w-6 place-items-center rounded-[4px] text-[#9aa7bc] transition-colors hover:bg-rose-400/10 hover:text-rose-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300/40">
                  <Trash2 size={12} aria-hidden />
                </button>
              </div>
              <p className="mt-1 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-[#c8d2df]">{note.body}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
