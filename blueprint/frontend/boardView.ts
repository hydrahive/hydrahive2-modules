// Reine Helfer für Board-Liste und Anzeige: Direktlink, Projektfilter, Projektname, Fehlertexte, Zeit.
import type { T } from "./texts.de"
import type { Board, BoardListItem, ProjectFilter, ProjectRef } from "./types"

/** Board-ID aus /blueprint?board=<id>. Alles andere als eine saubere Zahl zählt nicht. */
export function linkedBoard(value: string | null | undefined): number | null {
  return value && /^[1-9]\d{0,14}$/.test(value) ? Number(value) : null
}

/** Das Board, das offen sein soll: das verlinkte, wenn es das gibt, sonst das erste der Liste. */
export function pickBoard(boards: readonly { id: number }[], wanted: number | null): number | null {
  if (wanted !== null && boards.some((board) => board.id === wanted)) return wanted
  return boards[0]?.id ?? null
}

export function filterBoards<B extends { project_id: string | null }>(boards: readonly B[], project: ProjectFilter): B[] {
  if (project === "all") return [...boards]
  return boards.filter((board) => (project === "none" ? board.project_id === null : board.project_id === project))
}

/** Filter, mit dem dieses Board in der Liste steht: bleibt, wenn er passt, sonst „alle“. */
export function projectShowing(board: Pick<BoardListItem, "project_id">, current: ProjectFilter): ProjectFilter {
  return filterBoards([board], current).length > 0 ? current : "all"
}

export function projectName(id: string | null, projects: readonly ProjectRef[], t: T): string {
  if (id === null) return t("no_project")
  return projects.find((project) => project.id === id)?.name ?? t("unknown_project")
}

/** Stand eines offenen Boards in die Liste eintragen. Dieselbe Liste, wenn sich für die Liste nichts geändert hat. */
export function mergeBoard(list: BoardListItem[], board: Board): BoardListItem[] {
  const has_proposal = board.proposal_json !== null
  let changed = false
  const next = list.map((item) => {
    const same = item.name === board.name && item.project_id === board.project_id && item.has_proposal === has_proposal
    if (item.id !== board.id || same) return item
    changed = true
    return { ...item, name: board.name, project_id: board.project_id, updated_at: board.updated_at, has_proposal }
  })
  return changed ? next : list
}

const ERROR_KEYS = {
  project_not_found: "project_error", boards_full: "boards_full", proposal_changed: "proposal_changed",
  no_proposal: "proposal_changed", board_not_found: "notice_gone", version_not_found: "version_gone",
} as const

/** Meldung für eine fehlgeschlagene Aktion (anlegen, Projekt ändern, übernehmen, wiederherstellen). */
export function errorText(error: unknown, t: T): string {
  const code = String((error as { code?: unknown } | null)?.code ?? "")
  if (code in ERROR_KEYS) return t(ERROR_KEYS[code as keyof typeof ERROR_KEYS])
  return t("action_error", { message: error instanceof Error ? error.message : String(error) })
}

/** Zeitstempel des Servers als Datum mit Uhrzeit in der Sprache der Oberfläche. */
export function formatStamp(value: string | null | undefined, locale: string): string {
  const date = value ? new Date(value) : null
  if (!date || Number.isNaN(date.getTime())) return value ?? ""
  return date.toLocaleString(locale.startsWith("de") ? "de" : "en", { dateStyle: "medium", timeStyle: "short" })
}
