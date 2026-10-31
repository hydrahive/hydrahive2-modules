import { api } from "@/shared/api-client"
import { BASE, tracksQuery, type Filter, type ScanState } from "./logic"
import type { Station, StationSettings } from "./stationLogic"

export interface Track {
  track_id: string; artist: string; album_artist: string; title: string; album: string; genre: string
  year: number | null; track_no: number | null; duration_s: number | null; bitrate: number | null
  sample_rate: number | null; format: string; state: string
}
export interface Stats {
  tracks: number; duration_s: number; artists: number; missing: number; errors: number
  formats: Record<string, number>; genres: { genre: string; count: number }[]; decades: { decade: number; count: number }[]
}
export interface Source { url: string | null; credential_name: string | null; state: string; last_scan_finished: string | null; last_scan_error: string | null }
export type Scan = ScanState & { added: number; updated: number; missing: number; errors: number; finished_at: string | null; error_code: string | null }

export const getTracks = (f: Filter, cursor: string) => api.get<{ items: Track[]; next_cursor: string | null }>(tracksQuery(f, cursor))
export const getStats = () => api.get<Stats>(`${BASE}/stats`)
export const getGenres = () => api.get<{ items: { genre: string; count: number }[] }>(`${BASE}/genres`)
export const getScan = () => api.get<Scan>(`${BASE}/scan`)
export const startScan = () => api.post<{ started: boolean }>(`${BASE}/scan`, {})
export const cancelScan = () => api.post<Scan>(`${BASE}/scan/cancel`, {})
export const getSource = () => api.get<Source>(`${BASE}/settings`)
export const saveSource = (url: string, credential_name: string) => api.put<Source>(`${BASE}/settings`, { url, credential_name })
export const testSource = (url: string, credential_name: string) =>
  api.post<{ ok: boolean; top_dirs: number }>(`${BASE}/settings/test`, { url, credential_name })
export const getCredentials = () => api.get<{ items: { name: string; url_pattern: string }[] }>(`${BASE}/credentials`)
export const getStation = () => api.get<Station>(`${BASE}/station`)
export const startStation = () => api.post<Station>(`${BASE}/station/start`, {})
export const stopStation = () => api.post<Station>(`${BASE}/station/stop`, {})
export const skipTitle = () => api.post<Station>(`${BASE}/station/skip`, {})
export const saveStation = (v: StationSettings) => api.put<Station>(`${BASE}/station/settings`, v)
// --- Programm (PLAN-PROGRAMM.md) ---
import type { Mix, Playlist, PlaylistItem, Preview, Program, QueueItem, Rules } from "./programLogic"
type Items<T> = { items: T[] }
export const getProgram = () => api.get<Program>(`${BASE}/program`)
export const setProgram = (mode: string, ref_id: string) => api.put<Program>(`${BASE}/program`, { mode, ref_id })
export const getPlaylists = () => api.get<Items<Playlist>>(`${BASE}/playlists`)
export const getPlaylist = (id: string) => api.get<Playlist & { items: PlaylistItem[] }>(`${BASE}/playlists/${id}`)
export const createPlaylist = (name: string) => api.post<Playlist>(`${BASE}/playlists`, { name })
export const updatePlaylist = (id: string, v: Partial<Pick<Playlist, "name" | "order_mode" | "at_end">>) => api.put<Playlist>(`${BASE}/playlists/${id}`, v)
export const deletePlaylist = (id: string) => api.delete<{ ok: boolean }>(`${BASE}/playlists/${id}`)
export const addToPlaylist = (id: string, track_ids: string[]) => api.post<{ added: number }>(`${BASE}/playlists/${id}/items`, { track_ids })
export const addSearchToPlaylist = (id: string, f: Record<string, unknown>) => api.post<{ added: number }>(`${BASE}/playlists/${id}/add-search`, f)
export const movePlaylistItem = (id: string, from: number, to: number) => api.post<{ ok: boolean }>(`${BASE}/playlists/${id}/move`, { from, to })
export const removePlaylistItem = (id: string, pos: number) => api.delete<{ ok: boolean }>(`${BASE}/playlists/${id}/items/${pos}`)
export const getFolders = () => api.get<Items<{ folder: string; count: number }>>(`${BASE}/folders`)
export const getMixes = () => api.get<Items<Mix>>(`${BASE}/mixes`)
export const previewMix = (rules: Partial<Rules>, allow_long: boolean) => api.post<Preview>(`${BASE}/mixes/preview`, { rules, allow_long })
export const createMix = (name: string, rules: Partial<Rules>, allow_long: boolean) => api.post<Mix>(`${BASE}/mixes`, { name, rules, allow_long })
export const updateMix = (id: string, name: string, rules: Partial<Rules>, allow_long: boolean) => api.put<Mix>(`${BASE}/mixes/${id}`, { name, rules, allow_long })
export const deleteMix = (id: string) => api.delete<{ ok: boolean }>(`${BASE}/mixes/${id}`)
export const getQueue = () => api.get<Items<QueueItem>>(`${BASE}/queue`)
export const enqueue = (track_id: string, front: boolean) => api.post<Items<QueueItem>>(`${BASE}/queue`, { track_id, front })
export const moveQueue = (id: number, pos: number) => api.put<Items<QueueItem>>(`${BASE}/queue/${id}`, { pos })
export const dequeue = (id: number) => api.delete<Items<QueueItem>>(`${BASE}/queue/${id}`)
export interface Exclude { rules: { genres: string[]; genre_parts: string[]; folders: string[] }; allow_long: boolean; suggestions: { folder: string; count: number; share: number }[] }
export const getExclude = () => api.get<Exclude>(`${BASE}/exclude`)
export const saveExclude = (rules: Exclude["rules"], allow_long: boolean) => api.put<Exclude>(`${BASE}/exclude`, { rules, allow_long })
