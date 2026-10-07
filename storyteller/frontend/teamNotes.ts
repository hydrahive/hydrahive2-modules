// T1d (Spec schreib-team.md §5): Hinweise/Notizen des Schreib-Teams. Rein, ohne React → testbar; Aufrufe unten.
import { call } from "./api"

export interface TeamNote {
  id: string; seq: number; kind: "hint" | "note"; title: string; text: string
  sources: { title?: string; url: string }[]
  author: string; status: "open" | "done" | "dismissed"; at: string
  scene_id?: string; chapter_id?: string; entity_id?: string
}

/** Sichtbarkeit im Reiter „Team“: aktuelle Szene, ihr Kapitel (inkl. dessen Szenen) oder ganzes Buch. */
export type NoteScope = "scene" | "chapter" | "book"

export function filterNotes(notes: TeamNote[], scope: NoteScope, sceneId: string, chapters: Record<string, string[]>): TeamNote[] {
  if (scope === "book") return notes
  if (scope === "scene") return notes.filter((n) => n.scene_id === sceneId)
  const chapterId = Object.keys(chapters).find((c) => chapters[c].includes(sceneId))
  const scenes = new Set(chapterId ? chapters[chapterId] : [sceneId])
  return notes.filter((n) => (n.scene_id && scenes.has(n.scene_id)) || (chapterId !== undefined && n.chapter_id === chapterId))
}

/** Offene Einträge je Szene (gelber Punkt im Navigator). */
export function countByScene(notes: TeamNote[]): Record<string, number> {
  const out: Record<string, number> = {}
  for (const n of notes) if (n.status === "open" && n.scene_id) out[n.scene_id] = (out[n.scene_id] ?? 0) + 1
  return out
}

/** Quellen-Link nur für http(s) – alles andere (javascript:, data:, Unsinn) wird nicht verlinkt. */
export function safeUrl(raw: string): string | null {
  try {
    const u = new URL(raw)
    return u.protocol === "http:" || u.protocol === "https:" ? u.toString() : null
  } catch { return null }
}

const notesPath = (pid: string, bid: string) => `/projects/${encodeURIComponent(pid)}/books/${encodeURIComponent(bid)}/notes`

export const notesApi = {
  list: (pid: string, bid: string) => call<TeamNote[]>("GET", notesPath(pid, bid)),
  setStatus: (pid: string, bid: string, id: string, status: TeamNote["status"]) =>
    call<TeamNote>("PATCH", `${notesPath(pid, bid)}/${encodeURIComponent(id)}`, { status }),
}
