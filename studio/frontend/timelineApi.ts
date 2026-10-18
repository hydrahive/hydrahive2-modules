import { api } from "@/shared/api-client"

/** Schnittfassung (Spec „Bauplan Etappe 4“ und „Etappe 5“): Bildspur V1 (magnetisch), Tonspuren A1 „Sprache“ und
 *  A2 „Musik“ (frei). Clips mit Lage auf der Zeitleiste und Ausschnitt im Medium. */
export interface TimelineClip {
  id: string
  kind: "video" | "image" | "placeholder" | "audio"
  start: number
  in: number
  out: number
  media_rel: string
  scene_id: string
  shot_id: string
  label: string
  /** Medium wurde gelöscht – der Clip steht als Platzhalter da (Ton: stummer Clip). */
  missing?: boolean
}

export interface Timeline {
  /** Projektordner für /api/files (nur in Antworten). */
  base?: string
  revision: number
  fps: number
  tracks: TimelineTrack[]
}

export type TrackId = "V1" | "A1" | "A2"
export interface TimelineTrack { id: TrackId; kind: "video" | "audio"; clips: TimelineClip[] }

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/timeline`

export const timelineApi = {
  get: (pid: string) => api.get<Timeline>(base(pid)),
  save: (pid: string, tl: Timeline) => api.put<Timeline>(base(pid), tl),
  fromPlan: (pid: string, replace = false) => api.post<Timeline>(`${base(pid)}/from-plan`, { replace }),
  /** Wellenform (Spitzenwerte 0–100, `per_second` je Sekunde); leer, wenn die Datei nicht lesbar ist. */
  waveform: (pid: string, rel: string) =>
    api.get<{ per_second: number; duration: number; peaks: number[] }>(`/modules/studio/projects/${encodeURIComponent(pid)}/waveform?rel=${encodeURIComponent(rel)}`),
}

/** Clips einer Spur (Standard V1, die Bildspur). */
export const clipsOf = (tl: Timeline | null, track: TrackId = "V1"): TimelineClip[] =>
  tl?.tracks.find((t) => t.id === track)?.clips ?? (track === "V1" ? tl?.tracks[0]?.clips ?? [] : [])

/** Alle Clips aller Spuren (Filmlänge, Zähler). */
export const allClips = (tl: Timeline | null): TimelineClip[] => tl?.tracks.flatMap((t) => t.clips) ?? []

/** Spur ersetzen; fehlende Tonspuren (Server vor Etappe 5) kommen leer dazu. */
export function withTrack(tl: Timeline, track: TrackId, clips: TimelineClip[]): Timeline {
  const ids: TrackId[] = ["V1", "A1", "A2"]
  return { ...tl, tracks: ids.map((id) => ({ id, kind: id === "V1" ? "video" : "audio", clips: id === track ? clips : clipsOf(tl, id) })) }
}
