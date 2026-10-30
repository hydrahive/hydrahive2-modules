// T1d – Reiter „Team“ (Spec schreib-team.md §5): Hinweise und Notizen der Helfer zur Szene, zum Kapitel oder zum Buch.
// Abhaken („Erledigt“) oder Verwerfen ändert nur den Eintrag, nie das Buch. Ohne Schreibrecht nur lesen.
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { AlertTriangle, Check, ChevronDown, ChevronRight, ExternalLink, Lightbulb, X } from "lucide-react"
import { filterNotes, notesApi, safeUrl, type NoteScope, type TeamNote } from "../teamNotes"
import type { BookState } from "../useBook"
import { NoteText } from "./NoteText"
import { TeamJobs } from "./TeamJobs"

interface Props { state: BookState; sceneId: string; onOpenScene: (id: string) => void }
const SCOPES: NoteScope[] = ["scene", "chapter", "book"]

export function TeamPanel({ state, sceneId, onOpenScene }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const { projectId, book, notes, setNotes, canWrite } = state
  const [scope, setScope] = useState<NoteScope>("scene")
  const [openId, setOpenId] = useState<string | null>(null)
  const [error, setError] = useState("")

  // Beim Öffnen des Reiters frisch laden (danach hält das Nachfragen im Chat-Betrieb die Liste aktuell).
  useEffect(() => {
    let alive = true
    notesApi.list(projectId, book.id)
      .then((list) => { if (alive) { setNotes(list); setError("") } })
      .catch((e: unknown) => { if (alive) setError(String(e)) })
    return () => { alive = false }
  }, [projectId, book.id, setNotes])

  const chapters = useMemo(() => Object.fromEntries(
    book.parts.flatMap((p) => p.chapters.map((c) => [c.id, c.scenes.map((s) => s.id)]))), [book])
  const titles = useMemo(() => Object.fromEntries(
    book.parts.flatMap((p) => p.chapters.flatMap((c) => c.scenes.map((s) => [s.id, s.title])))), [book])
  const shown = filterNotes(notes ?? [], scope, sceneId, chapters)

  const setStatus = async (n: TeamNote, status: TeamNote["status"]) => {
    try {
      await notesApi.setStatus(projectId, book.id, n.id, status)
      setNotes((all) => (all ?? []).filter((x) => x.id !== n.id))
    } catch (e) { setError(String(e)) }
  }
  const when = (iso: string) => new Date(iso).toLocaleString(i18n.language, { dateStyle: "short", timeStyle: "short" })

  return (
    <div className="st-team-panel space-y-3 text-sm">
      <TeamJobs state={state} sceneId={sceneId} />
      <div role="radiogroup" aria-label={t("team_scope")} className="flex gap-1 rounded-lg bg-[rgb(var(--hh-s-innen,17_24_39))] p-1 text-xs">
        {SCOPES.map((s) => (
          <button key={s} role="radio" aria-checked={scope === s} onClick={() => setScope(s)}
            className={`flex-1 rounded px-2 py-1 ${scope === s ? "bg-[#69d7ff]/30 text-[#c8f2ff]" : "text-[#c8d2df] hover:text-[#e8eef8]"}`}>
            {t(`team_scope_${s}`)}
          </button>
        ))}
      </div>
      {error && <p className="text-xs text-red-200" role="alert">{error}</p>}
      {notes === null ? <p className="text-xs text-[#9aa7bc]">…</p> : shown.length === 0 ? (
        <p className="st-team-empty rounded-lg border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))] p-3 text-xs text-[#9aa7bc]">{t("team_empty")}</p>
      ) : (
        <ul className="space-y-2">
          {shown.map((n) => {
            const open = openId === n.id
            return (
              <li key={n.id} className="st-team-note rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] p-2">
                <button onClick={() => setOpenId(open ? null : n.id)} className="flex w-full items-start gap-2 text-left" aria-expanded={open}>
                  {n.kind === "hint"
                    ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" aria-label={t("team_kind_hint")} />
                    : <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-sky-300" aria-label={t("team_kind_note")} />}
                  <span className="min-w-0 flex-1">
                    <span className="block text-[#e8eef8]">{n.title}</span>
                    <span className="block truncate text-xs text-[#9aa7bc]">{n.author} · {when(n.at)}{n.scene_id && scope !== "scene" ? ` · ${titles[n.scene_id] ?? t("team_scene_gone")}` : ""}</span>
                  </span>
                  {open ? <ChevronDown className="h-4 w-4 text-[#9aa7bc]" /> : <ChevronRight className="h-4 w-4 text-[#9aa7bc]" />}
                </button>
                {open && (
                  <div className="mt-2 space-y-2 pl-6">
                    <NoteText text={n.text} />
                    {n.sources.length > 0 && (
                      <ul className="space-y-0.5 text-xs">
                        {n.sources.map((s, i) => {
                          const url = safeUrl(s.url)
                          return <li key={i}>{url
                            ? <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sky-300 hover:underline"><ExternalLink className="h-3 w-3" />{s.title || url}</a>
                            : <span className="text-[#9aa7bc]">{s.title || s.url}</span>}</li>
                        })}
                      </ul>
                    )}
                    <div className="flex flex-wrap gap-2">
                      {n.scene_id && titles[n.scene_id] && n.scene_id !== sceneId && (
                        <button onClick={() => onOpenScene(n.scene_id as string)} className="rounded px-2 py-0.5 text-xs text-[#69d7ff] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">{t("team_go_scene")}</button>
                      )}
                      {canWrite && <>
                        <button onClick={() => { void setStatus(n, "done") }} className="inline-flex items-center gap-1 rounded bg-emerald-700/70 px-2 py-0.5 text-xs text-white"><Check className="h-3 w-3" />{t("team_done")}</button>
                        <button onClick={() => { void setStatus(n, "dismissed") }} className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"><X className="h-3 w-3" />{t("team_dismiss")}</button>
                      </>}
                    </div>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
