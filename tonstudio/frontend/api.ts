import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { GenerateResult, LibraryItem, MusicModel, MusicRequest, Song, SongSummary } from "./types"

const BASE = "/modules/tonstudio"
const P = (pid: string) => `${BASE}/projects/${encodeURIComponent(pid)}`

export const tonstudioApi = {
  models: (): Promise<MusicModel[]> => api.get<MusicModel[]>(`${BASE}/models`),

  songs: (pid: string): Promise<SongSummary[]> => api.get<SongSummary[]>(`${P(pid)}/songs`),
  createSong: (pid: string, title: string): Promise<Song> => api.post<Song>(`${P(pid)}/songs`, { title }),
  getSong: (pid: string, id: string): Promise<Song> => api.get<Song>(`${P(pid)}/songs/${id}`),
  saveSong: (pid: string, song: Song): Promise<Song> =>
    api.put<Song>(`${P(pid)}/songs/${song.id}`, { ...song, expected_version: song.version }),
  trashSong: (pid: string, id: string): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${P(pid)}/songs/${id}`),
  trash: (pid: string): Promise<SongSummary[]> => api.get<SongSummary[]>(`${P(pid)}/trash`),
  restoreSong: (pid: string, id: string): Promise<{ ok: boolean }> =>
    api.post<{ ok: boolean }>(`${P(pid)}/trash/${id}/restore`, {}),

  library: (pid: string): Promise<LibraryItem[]> => api.get<LibraryItem[]>(`${P(pid)}/library`),
  upload: (pid: string, file: File): Promise<LibraryItem> => {
    const form = new FormData()
    form.append("file", file)
    return api.postForm<LibraryItem>(`${P(pid)}/library/upload`, form)
  },
  deleteClip: (pid: string, source_rel: string): Promise<{ ok: boolean }> =>
    api.post<{ ok: boolean }>(`${P(pid)}/library/delete`, { source_rel }),

  generate: (pid: string, model: string, request: MusicRequest): Promise<GenerateResult> =>
    api.post<GenerateResult>(`${P(pid)}/generate`, { model, request }),
}

/** URL für <audio>: eigene Modul-Route, Token als Query (der Kern erlaubt das für Modul-Router). */
export function audioUrl(pid: string, rel: string): string {
  const token = useAuthStore.getState().token
  const t = token ? `&token=${encodeURIComponent(token)}` : ""
  return `/api${P(pid)}/file?rel=${encodeURIComponent(rel)}${t}`
}

export function fmtDuration(s: number | null | undefined): string {
  if (!s || s <= 0) return "–"
  const m = Math.floor(s / 60)
  return `${m}:${String(Math.round(s % 60)).padStart(2, "0")}`
}
