import { api } from "@/shared/api-client"

/** Medienart in der Studio-Bibliothek (Backend: backend/library.py). */
export type MediaKind = "video" | "image" | "audio" | "music" | "element"
export type Origin = "ai" | "upload"
export type Source = "atelier" | "videoeditor" | "tonstudio" | "studio" | "studio_free" | "studio_render"

export interface LibraryItem {
  id: string
  kind: MediaKind
  origin: Origin
  source: Source
  name: string
  rel: string
  abs: string
  size: number
  created_at: string
  duration?: number
  prompt?: string
  model?: string
  thumb_abs?: string
}

export interface StudioProject {
  id: string
  name: string
}

export const studioApi = {
  projects: () => api.get<{ projects: StudioProject[] }>("/modules/studio/projects"),
  library: (projectId: string) =>
    api.get<{ items: LibraryItem[]; truncated: boolean }>(`/modules/studio/projects/${encodeURIComponent(projectId)}/library`),
}
