import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { GeneratedTrack, Track } from "./types"

const BASE = "/modules/musicplayer"

export const musicApi = {
  list: (): Promise<Track[]> => api.get<Track[]>(`${BASE}/tracks`),

  upload: (file: File, title: string): Promise<{ id: number; title: string }> => {
    const form = new FormData()
    form.append("file", file)
    if (title) form.append("title", title)
    return api.postForm<{ id: number; title: string }>(`${BASE}/tracks`, form)
  },

  remove: (id: number): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${BASE}/tracks/${id}`),

  /** Stream-URL fürs <audio>-Tag — Auth via ?token= (Tag kann keinen Header setzen). */
  streamUrl: (id: number): string => {
    const token = useAuthStore.getState().token ?? ""
    return `/api${BASE}/tracks/${id}/stream?token=${encodeURIComponent(token)}`
  },

  // --- Import generierter Musik (Admin) ---
  listGenerated: (): Promise<GeneratedTrack[]> =>
    api.get<GeneratedTrack[]>(`${BASE}/generated`),

  importGenerated: (path: string): Promise<{ id: number; title: string }> =>
    api.post<{ id: number; title: string }>(`${BASE}/generated/import`, { path }),
}
