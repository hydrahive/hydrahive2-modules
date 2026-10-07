// Storyteller – Server-Aufrufe (Ablage im Projektordner, KI). Fehler kommen als StoryApiError
// mit Code und – bei 409 – dem aktuellen Stand auf dem Server (`current`).
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { BookKind, EntityKind, GhostSettings, SceneOrigin, SceneStatus } from "./model"
import type { OutlineProposal } from "./chatApi"
import type { EntityProposal } from "./entityProposal"
import type { InfoProposal } from "./infoProposal"
import type { SuggestAction } from "./suggest"

const BASE = "/api/modules/storyteller"

export class StoryApiError extends Error {
  readonly status: number
  readonly code: string
  readonly current: unknown
  constructor(status: number, code: string, current?: unknown, message?: string) {
    super(message ?? code)
    this.status = status
    this.code = code
    this.current = current
  }
}

export interface ServerBook {
  id: string; title: string; kind: BookKind; language: string; audience: string; idea: string
  notes: string; model: string; ghost: GhostSettings; version: number; created_at: string; updated_at: string
}
export interface ServerBookInfo extends ServerBook { words: number }
export interface ServerScene {
  id: string; title: string; summary: string; pov: string; status: SceneStatus; origin: SceneOrigin; text: string
  version: number; updated_at: string
}
export interface GhostEstimate { model: string; length_words: number; sections: number; input_tokens: number; output_tokens: number }
export interface ServerEntity {
  id: string; kind: EntityKind; name: string; aliases: string[]; description: string; fields: { key: string; value: string }[]
}
export interface ServerStructure {
  version: number
  parts: { id: string; title: string; chapters: { id: string; title: string; scenes: string[] }[] }[]
  entities: ServerEntity[]
}
/** Abgelegter Ghostwriter-Vorschlag (Szene hatte Text oder wurde während des Laufs geändert). */
export interface ProposalInfo {
  scene_id: string; run_id: string; model: string; base_version: number; words: number; at: string
  /** Ab 0.6.0: Herkunft (Ghostwriter-Lauf oder Agent im Chat), Chat-Sitzung, Notiz des Agenten. */
  source?: "run" | "agent"; session_id?: string; note?: string
  /** Ab 0.10.2: Wortzahl der Szene beim Ablegen (Warnung bei stark verkürzendem Vorschlag). */
  scene_words?: number
}
export interface ServerFull {
  book: ServerBook; structure: ServerStructure; scenes: Record<string, ServerScene>
  /** Ab 0.4.0: Schreibrecht im Projekt (Oberfläche sperrt Knöpfe) und offene Vorschläge. */
  can_write?: boolean; proposals?: ProposalInfo[]
  /** Ab 0.7.0: offene Vorschläge für Szenen-Infos (G4b). */
  info_proposals?: InfoProposal[]
  /** Ab 0.8.0: offene Steckbrief-Vorschläge (G4c). */
  entity_proposals?: EntityProposal[]
  /** Ab 0.9.0: offener Gliederungs-Vorschlag des Agenten (G4d), sonst null. */
  outline_proposal?: OutlineProposal | null
}
export interface SnapshotInfo { id: string; at: string; words: number; text?: string }
export interface Created { scene: ServerScene; structure: ServerStructure }

export const authHeader = (): Record<string, string> => {
  const token = useAuthStore.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/** Fehler aus einer Server-Antwort lesen (auch für den Ghostwriter-Stream). */
export async function errorFrom(res: Response): Promise<StoryApiError> {
  if (res.status === 401) useAuthStore.getState().logout()
  const data = await res.json().catch(() => ({}))
  const d = (data as { detail?: unknown }).detail
  const obj = typeof d === "object" && d !== null && !Array.isArray(d) ? (d as Record<string, unknown>) : null
  const code = res.status === 401 ? "not_authenticated" : obj && typeof obj.code === "string" ? obj.code : `http_${res.status}`
  const msg = obj && typeof obj.message === "string" ? obj.message : typeof d === "string" ? d : undefined
  return new StoryApiError(res.status, code, obj?.current, msg)
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw await errorFrom(res)
  return (await res.json().catch(() => ({}))) as T
}

const p = (projectId: string) => `/projects/${encodeURIComponent(projectId)}`
const b = (projectId: string, bookId: string) => `${p(projectId)}/books/${encodeURIComponent(bookId)}`
export const storyBase = (pid: string, bid: string) => `${BASE}${b(pid, bid)}`

export const storyApi = {
  listBooks: (pid: string) => call<ServerBookInfo[]>("GET", `${p(pid)}/books`),
  createBook: (pid: string, f: { title: string; kind: BookKind; language: string; audience: string; idea: string }) =>
    call<ServerBook>("POST", `${p(pid)}/books`, f),
  importBook: (pid: string, payload: unknown) => call<ServerBook>("POST", `${p(pid)}/books/import`, payload),
  openBook: (pid: string, bid: string) => call<ServerFull>("GET", b(pid, bid)),
  patchBook: (pid: string, bid: string, baseVersion: number, patch: Partial<Omit<ServerBook, "ghost">> & { ghost?: Partial<GhostSettings> }) =>
    call<ServerBook>("PATCH", b(pid, bid), { ...patch, base_version: baseVersion }),
  deleteBook: (pid: string, bid: string) => call<{ ok: boolean }>("DELETE", b(pid, bid)),
  putStructure: (pid: string, bid: string, baseVersion: number, structure: Omit<ServerStructure, "version">) =>
    call<ServerStructure>("PUT", `${b(pid, bid)}/structure`, { base_version: baseVersion, structure }),
  addScene: (pid: string, bid: string, chapterId: string, title: string, after?: string) =>
    call<Created>("POST", `${b(pid, bid)}/scenes`, { chapter_id: chapterId, title, after: after ?? null }),
  addChapter: (pid: string, bid: string, partId: string, title: string, sceneTitle: string) =>
    call<Created>("POST", `${b(pid, bid)}/chapters`, { part_id: partId, title, scene_title: sceneTitle }),
  putScene: (pid: string, bid: string, sid: string, baseVersion: number, patch: Partial<ServerScene>) =>
    call<ServerScene>("PUT", `${b(pid, bid)}/scenes/${encodeURIComponent(sid)}`, { ...patch, base_version: baseVersion }),
  deleteScene: (pid: string, bid: string, sid: string) =>
    call<ServerStructure>("DELETE", `${b(pid, bid)}/scenes/${encodeURIComponent(sid)}`),
  listSnapshots: (pid: string, bid: string, sid: string) =>
    call<SnapshotInfo[]>("GET", `${b(pid, bid)}/scenes/${encodeURIComponent(sid)}/snapshots`),
  addSnapshot: (pid: string, bid: string, sid: string, text?: string) =>
    call<SnapshotInfo>("POST", `${b(pid, bid)}/scenes/${encodeURIComponent(sid)}/snapshots`, text === undefined ? {} : { text }),
  getSnapshot: (pid: string, bid: string, sid: string, snapId: string) =>
    call<SnapshotInfo>("GET", `${b(pid, bid)}/scenes/${encodeURIComponent(sid)}/snapshots/${encodeURIComponent(snapId)}`),
  suggest: (pid: string, bid: string, body: { scene_id: string; action: SuggestAction; selection: string; model?: string }) =>
    call<{ proposal: string; model: string }>("POST", `${b(pid, bid)}/ai/suggest`, body),
  ghostEstimate: (pid: string, bid: string, sid: string, lengthWords?: number) =>
    call<GhostEstimate>("GET", `${b(pid, bid)}/ghost/estimate?scene_id=${encodeURIComponent(sid)}${lengthWords ? `&length_words=${lengthWords}` : ""}`),
  ghostSummarize: (pid: string, bid: string, sid: string) =>
    call<{ kept: boolean; scene: ServerScene }>("POST", `${b(pid, bid)}/ghost/summarize`, { scene_id: sid }),
}
