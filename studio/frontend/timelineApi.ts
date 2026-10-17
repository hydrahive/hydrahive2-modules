import { api } from "@/shared/api-client"

/** Schnittfassung (Spec „Bauplan Etappe 4“): eine Videospur V1, Clips mit Lage auf der Zeitleiste und Ausschnitt im Medium. */
export interface TimelineClip {
  id: string
  kind: "video" | "image" | "placeholder"
  start: number
  in: number
  out: number
  media_rel: string
  scene_id: string
  shot_id: string
  label: string
  /** Medium wurde gelöscht – der Clip steht als Platzhalter da. */
  missing?: boolean
}

export interface Timeline {
  /** Projektordner für /api/files (nur in Antworten). */
  base?: string
  revision: number
  fps: number
  tracks: { id: string; kind: "video"; clips: TimelineClip[] }[]
}

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/timeline`

export const timelineApi = {
  get: (pid: string) => api.get<Timeline>(base(pid)),
  save: (pid: string, tl: Timeline) => api.put<Timeline>(base(pid), tl),
  fromPlan: (pid: string, replace = false) => api.post<Timeline>(`${base(pid)}/from-plan`, { replace }),
}

export const clipsOf = (tl: Timeline | null): TimelineClip[] => tl?.tracks[0]?.clips ?? []
