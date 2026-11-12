export type SaveState = "saved" | "saving" | "error" | "too_long" | "title_required" | "gone"

type RequestError = { status?: unknown; code?: unknown }

export function beginSave(): SaveState {
  return "saving"
}

export function saveStateForError(error: unknown): SaveState {
  const { status, code } = (error ?? {}) as RequestError
  if (code === "title_required") return "title_required"
  if (code === "title_too_long" || code === "body_too_long") return "too_long"
  // Die Idee wurde inzwischen gelöscht (anderes Fenster, Agent). Ein unbekanntes Projekt ist etwas anderes.
  if (status === 404 && code === "idea_not_found") return "gone"
  // Ohne benannten Fehler kommt 422 aus der Feldprüfung: eine Längengrenze wurde überschritten.
  if (status === 422 && code === undefined) return "too_long"
  return "error"
}

export function persist(save: () => Promise<unknown>): Promise<SaveState> {
  return save()
    .then(() => "saved" as const)
    .catch((error: unknown) => saveStateForError(error))
}

/** Was am Entwurf das Speichern der Kopfzeile verhindert, bevor etwas gesendet wird. */
export function draftProblem(title: string): SaveState | null {
  return title.trim() ? null : "title_required"
}

interface Draft {
  title: string
  body: string
}

/** Was vom Entwurf zu senden ist. Eine leere Kopfzeile wird nie gesendet, die Beschreibung trotzdem. */
export function pendingChanges(draft: Draft, stored: Draft): Partial<Draft> {
  const changes: Partial<Draft> = {}
  const title = draft.title.trim()
  if (title && title !== stored.title) changes.title = title
  if (draft.body !== stored.body) changes.body = draft.body
  return changes
}

type Translate = (key: "project_error" | "full_error" | "gone" | "too_long" | "title_required" | "action_error"
  | "task_linked_error" | "tasks_missing_error" | "blueprint_missing_error" | "boards_full_error",
  vars?: Record<string, string | number>) => string

/** Meldung für eine fehlgeschlagene Aktion (anlegen, Status, Projekt, löschen). */
export function errorText(error: unknown, t: Translate): string {
  const { code } = (error ?? {}) as RequestError
  if (code === "project_not_found") return t("project_error")
  if (code === "ideas_full") return t("full_error")
  if (code === "task_already_linked") return t("task_linked_error")
  if (code === "tasks_not_installed") return t("tasks_missing_error")
  if (code === "blueprint_not_installed") return t("blueprint_missing_error")
  if (code === "boards_full") return t("boards_full_error")
  const state = saveStateForError(error)
  if (state === "gone" || state === "title_required") return t(state)
  if (state === "too_long" && code !== undefined) return t("too_long")
  const message = error instanceof Error ? error.message : String(error)
  return t("action_error", { message })
}
