import { useEffect, useState } from "react"
import { Markdown } from "@/features/chat/Markdown"
import { ideasApi } from "../api"
import { detailState, foreignStamp } from "../foreign"
import type { T } from "../texts.de"
import type { ForeignIdea, ForeignIdeaFull } from "../types"
import { ForeignBadge } from "./ForeignBadge"
import { BADGE, ERROR_BOX, PANEL, STATUS_BADGE } from "./styles"

interface Props {
  idea: ForeignIdea
  locale: string
  t: T
  /** Nur für Tests: Volltext direkt vorgeben statt laden. */
  initial?: ForeignIdeaFull | null
}

// Detailansicht einer fremden Idee, nur lesen (Spec §Oberfläche, AK G14): Ideentext und Anmerkungen live.
// Ursprung offline → Snapshot mit „Stand vom …“ oder nur Metadaten mit „<instanz> zuletzt gesehen am …“;
// Hub offline → Metadaten aus der Kopie mit „Hub nicht erreichbar“. Kein Bearbeiten, Status, Löschen,
// Verschieben, keine Anmerkung und kein „Task daraus machen“ (Bearbeiten kommt mit G4).
export function ForeignIdeaDetail({ idea, locale, t, initial }: Props) {
  const [full, setFull] = useState<ForeignIdeaFull | null>(initial ?? null)
  const [error, setError] = useState(false)
  const name = idea.origin_name || idea.origin_fp.slice(0, 12)

  useEffect(() => {
    if (initial !== undefined) return
    let cancelled = false
    ideasApi.foreign(idea.origin_fp, idea.item_id)
      .then((r) => { if (!cancelled) setFull(r) })
      .catch(() => { if (!cancelled) setError(true) })
    return () => { cancelled = true }
  }, [idea.origin_fp, idea.item_id, initial])

  const state = full ? detailState(full) : null
  const body = full?.content?.body ?? ""
  const notes = full?.content?.notes ?? []
  const hint =
    state === "hub_unreachable" ? t("foreign_hub_unreachable")
    : state === "snapshot" ? t("foreign_snapshot", { stand: foreignStamp(full?.snapshot_at, locale) })
    : state === "origin_offline" ? t("foreign_last_seen", { name, seen: foreignStamp(full?.last_seen, locale) })
    : null

  return (
    <article className={`${PANEL} space-y-4 p-4`} data-testid="foreign-detail" data-state={state ?? "loading"}>
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <ForeignBadge idea={idea} locale={locale} t={t} />
          <span className={`${BADGE} ${STATUS_BADGE[idea.status]}`}>{t(`status_${idea.status}`)}</span>
          {idea.project_name && <span className="text-[11px] text-[#9aa7bc]">{idea.project_name}</span>}
        </div>
        <h2 className="break-words text-lg font-bold text-[#e8eef8]">{idea.title}</h2>
        <p className="text-[11px] text-[#9aa7bc]">{t("foreign_owned_by", { name })}</p>
      </header>
      {error && <p role="alert" className={ERROR_BOX}>{t("foreign_detail_error")}</p>}
      {!full && !error && <p className="text-xs text-[#9aa7bc]">{t("foreign_detail_loading")}</p>}
      {hint && <p className="text-xs text-amber-200/90">{hint}</p>}
      {full && (state === "live" || state === "snapshot") && (
        body.trim() ? <Markdown text={body} /> : <p className="text-xs text-[#9aa7bc]">{t("body_empty_preview")}</p>
      )}
      {notes.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-sm font-bold text-[#e8eef8]">{t("notes_title")}</h3>
          <ul className="space-y-2">
            {notes.map((note, index) => (
              <li key={`${note.created_at}-${index}`}
                className="rounded-[6px] border border-[rgb(var(--hh-s-rand,52_66_92))] bg-[rgb(var(--hh-s-tief,14_20_31))] px-3 py-2">
                <div className="flex items-center gap-2 text-[11px] text-[#9aa7bc]">
                  <span className="font-semibold text-[#c8d2df]">
                    {note.agent_name || t(note.author === "agent" ? "note_author_agent" : "note_author_system")}
                  </span>
                  <span>{foreignStamp(note.created_at, locale)}</span>
                </div>
                <p className="mt-1 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-[#c8d2df]">{note.body}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}
