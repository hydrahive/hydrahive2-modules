import { api } from "@/shared/api-client"
import { BASE, tracksQuery, type Filter, type ScanState } from "./logic"

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
