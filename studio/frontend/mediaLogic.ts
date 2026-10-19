/** Medien löschen und herunterladen (C1): reine Hilfen + API. Backend: backend/media.py. */
import { api } from "@/shared/api-client"
import type { LibraryItem } from "./api"

export interface MediaUsage {
  own: boolean
  shots: { scene_id: string; shot_id: string; label: string }[]
  clips: number
  elements: { id: string; name: string }[]
}

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/media`

export const mediaApi = {
  usage: (pid: string, rel: string) => api.get<MediaUsage>(`${base(pid)}/usage?rel=${encodeURIComponent(rel)}`),
  remove: (pid: string, rel: string) => api.delete<{ deleted: string }>(`${base(pid)}?rel=${encodeURIComponent(rel)}`),
}

/** Zeilen für die Rückfrage: wo die Datei benutzt wird (Text-Schlüssel + Werte). */
export function usageLines(u: MediaUsage): { key: string; o: Record<string, unknown> }[] {
  const out: { key: string; o: Record<string, unknown> }[] = []
  if (u.shots.length) out.push({ key: "media_used_shots", o: { count: u.shots.length, names: u.shots.map((s) => s.label).join(", ") } })
  if (u.clips) out.push({ key: "media_used_clips", o: { count: u.clips } })
  if (u.elements.length) out.push({ key: "media_used_elements", o: { count: u.elements.length, names: u.elements.map((e) => e.name).join(", ") } })
  return out
}

/** Dateiname beim Herunterladen: lesbarer Name (ohne / \ : …) + Endung der Datei. */
export function downloadName(item: Pick<LibraryItem, "name" | "rel">): string {
  const file = item.rel.split("/").pop() ?? ""
  const dot = file.lastIndexOf(".")
  const ext = dot > 0 ? file.slice(dot) : ""
  const stem = (item.name || "").replace(/[\\/:*?"<>|]+/g, "-").trim()
  return stem ? `${stem}${ext}` : file
}

/** Ablauf „Löschen“ (C1) ohne React: Verwendung holen → Rückfrage zeigen → löschen → neu laden + Meldung.
 *  `show(usage)` öffnet bzw. füllt die Rückfrage, `fail(e)` meldet einen Fehler. */
export const deleteFlow = {
  ask: (pid: string, rel: string, show: (u: MediaUsage) => void, fail: (e: unknown) => void) =>
    mediaApi.usage(pid, rel).then(show, fail),
  confirm: async (pid: string, rel: string, done: (rel: string) => void) => {
    await mediaApi.remove(pid, rel)
    done(rel)
  },
}
