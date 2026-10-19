import { api } from "@/shared/api-client"
import type { Job } from "./planApi"

/** Fertiger Film (Backend: backend/render.py, Spec „Bauplan 4d“). */
export interface RenderItem {
  rel: string
  /** Pfad für /api/files */
  abs: string
  name: string
  duration: number | null
  width: number | null
  height: number | null
  created_at: string | null
  /** Clips, deren Medium beim Rendern fehlte (als Platzhalter im Film) */
  missing: number | null
  clips: number | null
  /** Sprachen der Untertitelspuren im Film (6c; abschaltbar, nicht eingebrannt) */
  subtitles?: string[]
}

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}`

export const renderApi = {
  start: (pid: string, subtitles = false) => api.post<Job>(`${base(pid)}/render`, subtitles ? { subtitles: true } : {}),
  list: (pid: string) => api.get<{ renders: RenderItem[] }>(`${base(pid)}/renders`),
}
