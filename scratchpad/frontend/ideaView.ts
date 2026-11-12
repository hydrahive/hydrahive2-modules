// Reine Funktionen für Liste und Detail: filtern, zählen, gruppieren, sortieren. Ohne React, ohne Netz.
import {
  OPEN_STATUSES, STATUSES,
  type Idea, type IdeaListItem, type ProjectFilter, type ProjectRef, type StatusCounts, type StatusFilter,
} from "./types"

const PREVIEW_CHARS = 160

export interface ProjectGroup {
  projectId: string | null
  /** null bei „ohne Projekt“ und bei Projekten, die es nicht mehr gibt. */
  name: string | null
  known: boolean
  ideas: IdeaListItem[]
}

/** Neueste Änderung zuerst. Die Zeitstempel haben ein festes Format und lassen sich als Text vergleichen. */
export function sortIdeas<T extends { id: string; updated_at: string }>(list: readonly T[]): T[] {
  return [...list].sort((a, b) =>
    a.updated_at < b.updated_at ? 1 : a.updated_at > b.updated_at ? -1 : a.id.localeCompare(b.id))
}

function inProject(idea: IdeaListItem, project: ProjectFilter): boolean {
  if (project === "all") return true
  if (project === "none") return idea.project_id === null
  return idea.project_id === project
}

export function filterIdeas(list: readonly IdeaListItem[], project: ProjectFilter, status: StatusFilter): IdeaListItem[] {
  return list.filter((idea) => {
    if (!inProject(idea, project)) return false
    if (status === "all") return true
    if (status === "open") return OPEN_STATUSES.includes(idea.status)
    return idea.status === status
  })
}

/** Anzahl je Status innerhalb des Projektfilters. Der Statusfilter spielt keine Rolle. */
export function countByStatus(list: readonly IdeaListItem[], project: ProjectFilter): StatusCounts {
  const counts = Object.fromEntries(STATUSES.map((status) => [status, 0])) as StatusCounts
  for (const idea of list) {
    if (inProject(idea, project) && idea.status in counts) counts[idea.status] += 1
  }
  return counts
}

export function openCount(counts: StatusCounts): number {
  return OPEN_STATUSES.reduce((sum, status) => sum + counts[status], 0)
}

/** Gruppen für „Alle Projekte“: Projekte nach Name, dann unbekannte, zuletzt „ohne Projekt“. */
export function groupByProject(list: readonly IdeaListItem[], projects: readonly ProjectRef[]): ProjectGroup[] {
  const names = new Map(projects.map((project) => [project.id, project.name]))
  const byProject = new Map<string | null, IdeaListItem[]>()
  for (const idea of list) {
    const bucket = byProject.get(idea.project_id)
    if (bucket) bucket.push(idea)
    else byProject.set(idea.project_id, [idea])
  }
  const groups: ProjectGroup[] = [...byProject.entries()].map(([projectId, ideas]) => ({
    projectId, ideas,
    name: projectId === null ? null : names.get(projectId) ?? null,
    known: projectId === null || names.has(projectId),
  }))
  const rank = (group: ProjectGroup) => (group.projectId === null ? 2 : group.known ? 0 : 1)
  return groups.sort((a, b) =>
    rank(a) - rank(b)
    || (a.name ?? a.projectId ?? "").localeCompare(b.name ?? b.projectId ?? "", undefined, { sensitivity: "base" }))
}

const IDEA_ID = /^[A-Za-z0-9-]{8,64}$/

/** ID aus dem Direktlink /scratchpad?idea=<id>. null bei allem, was keine ID sein kann. */
export function linkedIdea(value: string | null | undefined): string | null {
  const id = (value ?? "").trim()
  return IDEA_ID.test(id) ? id : null
}

/** Projektfilter, der die Idee zeigt: der aktuelle, wenn er passt, sonst „alle Projekte“. */
export function projectShowing(idea: IdeaListItem, current: ProjectFilter): ProjectFilter {
  return inProject(idea, current) ? current : "all"
}

/** Statusfilter, der die Idee zeigt: der aktuelle, wenn er passt, sonst „Offen“ oder „Alle“. */
export function statusShowing(idea: IdeaListItem, current: StatusFilter): StatusFilter {
  if (filterIdeas([idea], "all", current).length > 0) return current
  return OPEN_STATUSES.includes(idea.status) ? "open" : "all"
}

export function upsertIdea(list: readonly IdeaListItem[], item: IdeaListItem): IdeaListItem[] {
  return sortIdeas([...list.filter((idea) => idea.id !== item.id), item])
}

export function toListItem(idea: Idea): IdeaListItem {
  const { body, notes, task: _task, board: _board, ...rest } = idea
  return {
    ...rest,
    body_preview: body.split(/\s+/).filter(Boolean).join(" ").slice(0, PREVIEW_CHARS),
    note_count: notes.length,
  }
}

/** Gemerkte Projektwahl nur übernehmen, wenn es das Projekt noch gibt. "" = ohne Projekt. */
export function validProject(id: string | null | undefined, projects: readonly ProjectRef[]): string {
  return id && projects.some((project) => project.id === id) ? id : ""
}

/** Zeitstempel des Backends (UTC, mit Mikrosekunden) als Datum. */
export function parseStamp(value: string): Date | null {
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?Z$/.exec(value ?? "")
  if (!match) return null
  const date = new Date(`${match[1]}${(match[2] ?? ".000").slice(0, 4).padEnd(4, "0")}Z`)
  return Number.isNaN(date.getTime()) ? null : date
}

const UNITS: Array<[Intl.RelativeTimeFormatUnit, number]> = [["day", 86_400_000], ["hour", 3_600_000], ["minute", 60_000]]

/** „vor 3 Tagen“, ab 30 Tagen das Datum. */
export function relativeTime(value: string, locale: string, now: number = Date.now()): string {
  const date = parseStamp(value)
  if (!date) return "—"
  const lang = locale.startsWith("de") ? "de" : "en"
  const diff = date.getTime() - now
  if (Math.abs(diff) >= 30 * 86_400_000) return date.toLocaleDateString(lang, { dateStyle: "medium" })
  const formatter = new Intl.RelativeTimeFormat(lang, { numeric: "auto" })
  for (const [unit, ms] of UNITS) {
    if (Math.abs(diff) >= ms || unit === "minute") return formatter.format(Math.round(diff / ms), unit)
  }
  return formatter.format(0, "minute")
}

/** Datum mit Uhrzeit in der Sprache der Oberfläche. */
export function formatStamp(value: string, locale: string): string {
  const date = parseStamp(value)
  if (!date) return "—"
  return date.toLocaleString(locale.startsWith("de") ? "de" : "en", { dateStyle: "medium", timeStyle: "short" })
}
