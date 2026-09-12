import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { GeneratedTrack, Track, TrackLibrary } from "./types"

const BASE = "/modules/musicplayer"
const projectBase = (projectId: string) => `${BASE}/projects/${encodeURIComponent(projectId)}`

export const musicApi = {
  list: (projectId: string): Promise<TrackLibrary> =>
    api.get<TrackLibrary>(`${projectBase(projectId)}/tracks`),

  upload: (projectId: string, file: File, title: string): Promise<{ id: number; title: string }> => {
    const form = new FormData()
    form.append("file", file)
    if (title) form.append("title", title)
    return api.postForm<{ id: number; title: string }>(`${projectBase(projectId)}/tracks`, form)
  },

  remove: (projectId: string, id: number): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${projectBase(projectId)}/tracks/${id}`),

  /** Stream-URL fürs <audio>-Tag — Auth via ?token= (Tag kann keinen Header setzen). */
  streamUrl: (projectId: string, id: number): string => {
    const token = useAuthStore.getState().token ?? ""
    return `/api${projectBase(projectId)}/tracks/${id}/stream?token=${encodeURIComponent(token)}`
  },

  /** Lädt mit Authorization-Header, damit der JWT nicht in URL oder Browser-History landet. */
  download: async (projectId: string, track: Track): Promise<void> => {
    const token = useAuthStore.getState().token
    const response = await fetch(
      `/api${projectBase(projectId)}/tracks/${track.id}/stream?download=1`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    )
    if (response.status === 401) useAuthStore.getState().logout()
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const blobUrl = URL.createObjectURL(await response.blob())
    const link = document.createElement("a")
    link.href = blobUrl
    link.download = `${track.title.replace(/[\\/:*?"<>|]+/g, "_") || `track-${track.id}`}.mp3`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(blobUrl)
  },

  listGenerated: (projectId: string): Promise<GeneratedTrack[]> =>
    api.get<GeneratedTrack[]>(`${projectBase(projectId)}/generated`),

  importGenerated: (projectId: string, path: string): Promise<{ id: number; title: string }> =>
    api.post<{ id: number; title: string }>(`${projectBase(projectId)}/generated/import`, { path }),
}
