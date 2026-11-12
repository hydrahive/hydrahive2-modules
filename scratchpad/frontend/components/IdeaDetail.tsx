import { useCallback, useEffect, useRef, useState } from "react"
import { Bot, Trash2 } from "lucide-react"
import { Markdown } from "@/features/chat/Markdown"
import { formatStamp } from "../ideaView"
import { beginSave, draftProblem, pendingChanges, saveStateForError, type SaveState } from "../saveState"
import type { T } from "../texts.de"
import { STATUSES, type Idea, type IdeaChanges, type IdeaStatus, type ProjectRef } from "../types"
import { IdeaNotes } from "./IdeaNotes"
import { IdeaTask } from "./IdeaTask"
import { BADGE, BUTTON, BUTTON_DANGER, ERROR_BOX, FIELD, LABEL, PANEL, SELECT } from "./styles"

const SAVE_DELAY_MS = 800

interface Props {
  idea: Idea
  projects: ProjectRef[]
  locale: string
  t: T
  onUpdate: (id: string, changes: IdeaChanges) => Promise<Idea>
  onRemove: (id: string) => Promise<void>
  onRemoveNote: (id: string, noteId: number) => Promise<void>
  tasksInstalled: boolean
  onCreateTask: (id: string) => Promise<unknown>
  /** Die Idee gibt es auf dem Server nicht mehr: aus der Liste nehmen, den Text aber stehen lassen. */
  onGone: (id: string) => void
  errorOf: (error: unknown) => string
}

const SAVE_TEXT: Record<SaveState, "saved" | "saving" | "not_saved" | "too_long" | "title_required" | "gone"> = {
  saved: "saved", saving: "saving", error: "not_saved", too_long: "too_long", title_required: "title_required", gone: "gone",
}

/** Eine Idee bearbeiten. Kopfzeile und Beschreibung speichern von selbst; die Seite setzt je Idee einen eigenen key. */
export function IdeaDetail({ idea, projects, locale, t, onUpdate, onRemove, onRemoveNote, tasksInstalled, onCreateTask, onGone, errorOf }: Props) {
  const [title, setTitle] = useState(idea.title)
  const [body, setBody] = useState(idea.body)
  const [saveState, setSaveState] = useState<SaveState>("saved")
  const [preview, setPreview] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [taskBusy, setTaskBusy] = useState(false)
  const draft = useRef({ title: idea.title, body: idea.body })
  const stored = useRef({ title: idea.title, body: idea.body })
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const queue = useRef<Promise<void>>(Promise.resolve())
  const alive = useRef(true)
  const gone = useRef(false)

  // Speichert, was sich seit dem letzten Stand geändert hat. Aufrufe laufen nacheinander, nie überlappend.
  const flush = useCallback(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = null
    queue.current = queue.current.then(async () => {
      if (gone.current) return
      const changes = pendingChanges(draft.current, stored.current)
      if (Object.keys(changes).length === 0) {
        if (alive.current) setSaveState(draftProblem(draft.current.title) ?? "saved")
        return
      }
      try {
        await onUpdate(idea.id, changes)
        // Gemerkt wird das Gesendete, nicht die Antwort: der Server glättet Leerraum in der Kopfzeile.
        stored.current = { ...stored.current, ...changes }
        if (alive.current) setSaveState(draftProblem(draft.current.title) ?? "saved")
      } catch (problem) {
        const state = saveStateForError(problem)
        if (state === "gone") {
          gone.current = true
          onGone(idea.id)
        }
        if (alive.current) setSaveState(state)
      }
    })
  }, [idea.id, onUpdate, onGone])

  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
      if (timer.current) flush()  // Wechsel zu einer anderen Idee: Ungespeichertes noch abschicken
    }
  }, [flush])

  function edit(field: "title" | "body", value: string) {
    draft.current = { ...draft.current, [field]: value }
    if (field === "title") setTitle(value)
    else setBody(value)
    if (gone.current) return
    setSaveState(beginSave())
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(flush, SAVE_DELAY_MS)
  }

  async function change(changes: IdeaChanges) {
    setActionError(null)
    try {
      await onUpdate(idea.id, changes)
    } catch (problem) {
      setActionError(errorOf(problem))
    }
  }

  async function act(run: () => Promise<void>) {
    setActionError(null)
    try {
      await run()
    } catch (problem) {
      setActionError(errorOf(problem))
    }
  }

  async function createTask() {
    setTaskBusy(true)
    flush()  // der Task übernimmt den gespeicherten Text: erst speichern, dann anlegen
    await queue.current
    // Ließ sich der Text nicht speichern, entsteht kein Task aus dem alten Stand. Der Speicherstatus zeigt den Grund.
    if (Object.keys(pendingChanges(draft.current, stored.current)).length === 0) {
      await act(async () => { await onCreateTask(idea.id) })
    }
    if (alive.current) setTaskBusy(false)
  }

  const failed = saveState === "error" || saveState === "too_long" || saveState === "title_required" || saveState === "gone"
  const projectKnown = idea.project_id === null || projects.some((item) => item.id === idea.project_id)

  return (
    <article className={`${PANEL} space-y-4 p-4`}>
      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        {idea.origin === "agent" && <span className={`${BADGE} gap-1 border-[#69d7ff]/40 bg-[#69d7ff]/10 text-[#9fe6ff]`}><Bot size={11} aria-hidden />{t("origin_agent")}</span>}
        <span role="status" className={failed ? "text-rose-200" : "text-[#9aa7bc]"}>{t(SAVE_TEXT[saveState])}</span>
        {saveState === "error" && <button type="button" onClick={flush} className={BUTTON}>{t("retry")}</button>}
        <span className="ml-auto text-[#9aa7bc]">{t("created_at", { date: formatStamp(idea.created_at, locale) })} · {t("updated_at", { date: formatStamp(idea.updated_at, locale) })}</span>
      </div>

      <div>
        <label htmlFor="idea-title" className={LABEL}>{t("detail_title_label")}</label>
        <input id="idea-title" value={title} maxLength={200} autoComplete="off" onChange={(event) => edit("title", event.target.value)}
          onBlur={flush} aria-invalid={saveState === "title_required"} className={`${FIELD} text-[15px] font-semibold`} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="idea-status" className={LABEL}>{t("detail_status_label")}</label>
          <select id="idea-status" value={idea.status} onChange={(event) => void change({ status: event.target.value as IdeaStatus })} className={SELECT}>
            {STATUSES.map((status) => <option key={status} value={status}>{t(`status_${status}`)}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="idea-project" className={LABEL}>{t("detail_project_label")}</label>
          <select id="idea-project" value={idea.project_id ?? ""} onChange={(event) => void change({ project_id: event.target.value || null })} className={SELECT}>
            <option value="">{t("no_project")}</option>
            {!projectKnown && <option value={idea.project_id ?? ""}>{t("unknown_project")}</option>}
            {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </div>
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between">
          <label htmlFor="idea-body" className={`${LABEL} mb-0`}>{t("detail_body_label")}</label>
          <button type="button" onClick={() => setPreview((shown) => !shown)} aria-pressed={preview} className={BUTTON}>{t(preview ? "edit" : "preview")}</button>
        </div>
        {preview ? (
          <div className="min-h-[16rem] overflow-auto rounded-[6px] border border-[rgb(var(--hh-s-rand,52_66_92))] bg-[rgb(var(--hh-s-tief,14_20_31))] px-4 py-3 text-[#c8d2df]">
            {body.trim() ? <Markdown text={body} /> : <p className="text-xs text-[#9aa7bc]">{t("body_empty_preview")}</p>}
          </div>
        ) : (
          <textarea id="idea-body" value={body} maxLength={50000} onChange={(event) => edit("body", event.target.value)} onBlur={flush}
            placeholder={t("form_body_placeholder")} className={`${FIELD} min-h-[16rem] resize-y font-mono text-[13px] leading-relaxed`} />
        )}
      </div>

      {actionError && <p role="alert" className={ERROR_BOX}>{actionError}</p>}

      <IdeaTask task={idea.task} installed={tasksInstalled} busy={taskBusy} t={t} onCreate={() => void createTask()} />

      <IdeaNotes notes={idea.notes} locale={locale} t={t} onRemove={(noteId) => void act(() => onRemoveNote(idea.id, noteId))} />

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[rgb(var(--hh-s-rand,52_66_92))] pt-3">
        {confirming ? (
          <>
            <span className="mr-auto text-xs text-rose-100">{t("delete_confirm")}</span>
            <button type="button" onClick={() => setConfirming(false)} className={BUTTON}>{t("cancel")}</button>
            <button type="button" onClick={() => void act(() => onRemove(idea.id))} className={BUTTON_DANGER}>{t("delete_yes")}</button>
          </>
        ) : (
          <button type="button" onClick={() => setConfirming(true)} className={BUTTON}><Trash2 size={13} aria-hidden />{t("delete")}</button>
        )}
      </div>
    </article>
  )
}
