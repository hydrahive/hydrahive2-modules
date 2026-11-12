import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react"
import { Lightbulb } from "lucide-react"
import { validProject } from "../ideaView"
import type { T } from "../texts.de"
import type { ProjectRef } from "../types"
import { BUTTON_PRIMARY, ERROR_BOX, FIELD, LABEL, PANEL, SELECT } from "./styles"

const REMEMBER_KEY = "scratchpad.lastProject"

interface Props {
  projects: ProjectRef[]
  t: T
  /** Legt die Idee an. Wirft bei Fehlern; der Text der Meldung kommt aus errorOf. */
  onCreate: (data: { title: string; body: string; project_id: string | null }) => Promise<unknown>
  errorOf: (error: unknown) => string
}

function remembered(): string {
  try {
    return localStorage.getItem(REMEMBER_KEY) ?? ""
  } catch {
    return ""
  }
}

function remember(projectId: string): void {
  try {
    localStorage.setItem(REMEMBER_KEY, projectId)
  } catch {
    // Privater Modus oder voller Speicher: die Wahl gilt dann nur bis zum Neuladen.
  }
}

/** Neue Idee wie eine Notiz: Kopfzeile, Beschreibung, Projekt. Ohne Agent, ohne Pflichtfelder außer der Kopfzeile. */
export function IdeaForm({ projects, t, onCreate, errorOf }: Props) {
  const [title, setTitle] = useState("")
  const [body, setBody] = useState("")
  const [project, setProject] = useState(remembered)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const titleRef = useRef<HTMLInputElement>(null)

  // Die gemerkte Wahl gilt nur, solange es das Projekt noch gibt. Die Liste kommt nach dem ersten Bild.
  const chosen = projects.length ? validProject(project, projects) : ""

  useEffect(() => {
    titleRef.current?.focus()
  }, [])

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    if (busy || !title.trim()) return
    setBusy(true)
    setError(null)
    try {
      await onCreate({ title: title.trim(), body, project_id: chosen || null })
      setTitle("")
      setBody("")
      titleRef.current?.focus()
    } catch (problem) {
      setError(errorOf(problem))
    } finally {
      setBusy(false)
    }
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) void submit()
  }

  function chooseProject(value: string) {
    setProject(value)
    remember(value)
  }

  return (
    <form onSubmit={submit} onKeyDown={onKeyDown} className={`${PANEL} space-y-3 p-4`}>
      <div>
        <label htmlFor="idea-new-title" className={LABEL}>{t("form_title_label")}</label>
        <input id="idea-new-title" ref={titleRef} value={title} maxLength={200} autoComplete="off"
          onChange={(event) => setTitle(event.target.value)} placeholder={t("form_title_placeholder")}
          className={`${FIELD} text-[15px] font-semibold`} />
      </div>
      <div>
        <label htmlFor="idea-new-body" className={LABEL}>{t("form_body_label")}</label>
        <textarea id="idea-new-body" value={body} maxLength={50000} rows={title || body ? 5 : 2}
          onChange={(event) => setBody(event.target.value)} placeholder={t("form_body_placeholder")}
          className={`${FIELD} resize-y font-mono text-[13px] leading-relaxed`} />
      </div>
      {error && <p role="alert" className={ERROR_BOX}>{error}</p>}
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[12rem] flex-1 sm:max-w-xs">
          <label htmlFor="idea-new-project" className={LABEL}>{t("form_project_label")}</label>
          <select id="idea-new-project" value={chosen} onChange={(event) => chooseProject(event.target.value)} className={SELECT}>
            <option value="">{t("no_project")}</option>
            {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </div>
        <span className="ml-auto hidden text-[11px] text-[#9aa7bc] sm:inline">{t("form_hint")}</span>
        <button type="submit" disabled={busy || !title.trim()} className={BUTTON_PRIMARY}>
          <Lightbulb size={14} aria-hidden />{t("form_submit")}
        </button>
      </div>
    </form>
  )
}
