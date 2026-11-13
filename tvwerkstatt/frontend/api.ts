import { api } from "@/shared/api-client"

export const BASE = "/modules/tvwerkstatt"

export interface TvwDevice {
  device_id: string; name: string; address: string; adb_port?: number; model?: string; android?: string
  sdk?: number; kind?: string; stock_home?: string; current_home?: string; adb_state?: string; checked_at?: string
  check?: TvwJob | null; action?: (TvwJob & { kind: "install" | "restore" }) | null
}
export interface TvwBuild {
  build_id: string; part: string; commit_id: string; sha256: string; package?: string; version?: string
  size?: number; signer?: string; state: string; log_tail?: string; created_at: string
}
export interface TvwJob {
  job_id: string; state: "running" | "done" | "failed" | string; step: string; error_code: string
  error_detail: string; started_by: string; created_at: string; updated_at: string
}
export type ContainerState = "missing" | "stopped" | "running" | "unknown"
export interface TvwState {
  incus: boolean; error_code: string; devices: TvwDevice[]; builds: TvwBuild[]
  container: ContainerState; setup: TvwJob | null; build?: TvwJob | null
}

export const getState = () => api.get<TvwState>(`${BASE}/state`)
export const startSetup = (acceptLicense: boolean) =>
  api.post<{ job_id: string }>(`${BASE}/setup`, { accept_license: acceptLicense })
export const stopContainer = () => api.post<{ container: ContainerState }>(`${BASE}/container/stop`, {})
export const removeContainer = () => api.delete<{ container: ContainerState }>(`${BASE}/container`)
export const addDevice = (name: string, address: string, port = 5555) =>
  api.post<{ device_id: string; job_id: string }>(`${BASE}/devices`, { name, address, port })
export const checkDevice = (id: string) =>
  api.post<{ job_id: string }>(`${BASE}/devices/${encodeURIComponent(id)}/check`, {})
export const removeDevice = (id: string) => api.delete<{ ok: boolean }>(`${BASE}/devices/${encodeURIComponent(id)}`)
export const startBuild = () => api.post<{ job_id: string }>(`${BASE}/build`, {})
export const installHome = (id: string) =>
  api.post<{ job_id: string }>(`${BASE}/devices/${encodeURIComponent(id)}/install`, { confirm: true })
export const restoreHome = (id: string) =>
  api.post<{ job_id: string }>(`${BASE}/devices/${encodeURIComponent(id)}/restore`, { confirm: true })

// --- Desktop (E2) --------------------------------------------------------------------------------------------
export type Mood = "morning" | "evening" | "night"
export interface TvwLook {
  dock: string[]; hidden: string[]; labels: Record<string, string>; columns: number; rows_below_dock: number
  background_color: string; wallpaper_dim: number; dock_opacity: number; rotation_minutes: number
  sky_intensity: number; clock_format: "12" | "24" | "system"; show_greeting: boolean; greeting_name: string
}
export interface TvwApp { package: string; label: string; version: string; has_banner: number; color: string }
export interface TvwWallpaper { wallpaper_id: string; mood: Mood; file_name: string; title: string; created_at: string }
export interface TvwDesktop {
  look: TvwLook; apps: TvwApp[]; wallpapers: TvwWallpaper[]; pushed_at: string; pushed_current: boolean
  read_job: TvwJob | null; push_job: TvwJob | null
}
const dev = (id: string) => `${BASE}/devices/${encodeURIComponent(id)}`
export const getDesktop = (id: string) => api.get<TvwDesktop>(`${dev(id)}/desktop`)
export const saveLook = (id: string, look: TvwLook) => api.put<{ look: TvwLook }>(`${dev(id)}/look`, look)
export const readApps = (id: string) => api.post<{ job_id: string }>(`${dev(id)}/apps/read`, {})
export const pushLook = (id: string) => api.post<{ job_id: string }>(`${dev(id)}/look/push`, { confirm: true })
export const uploadWallpaper = (id: string, mood: Mood, file: File) => {
  const form = new FormData()
  form.append("mood", mood)
  form.append("file", file)
  return api.postForm<{ wallpaper: TvwWallpaper }>(`${dev(id)}/wallpapers`, form)
}
export const deleteWallpaper = (id: string, wid: string) =>
  api.delete<{ ok: boolean }>(`${dev(id)}/wallpapers/${encodeURIComponent(wid)}`)
export const appImagePath = (id: string, pkg: string) => `/api${dev(id)}/apps/${encodeURIComponent(pkg)}/image`
export const wallpaperPath = (id: string, wid: string) => `/api${dev(id)}/wallpapers/${encodeURIComponent(wid)}/image`

// --- Entrümpeln (E4, Teil 1: nur lesen) ---------------------------------------------------------------------
export type DebloatGroup = "tracking" | "ads" | "demo" | "home" | "help" | "other"
export interface TvwDebloatRow {
  package: string; state: "on" | "off"; recommended: boolean; of: number; kept: number; lists: number; note: string
  group: DebloatGroup; locked: "" | "core" | "home"
}
export interface TvwDebloatView {
  lists_used: string[]; score: number; total_lists: number; packages: TvwDebloatRow[]; off_count: number
  recommended_on: number; read_at: string; commit_id: string; ours: string[]; back_on: string[]
}
export interface TvwDebloat {
  view: TvwDebloatView | null; read_job: TvwJob | null; switch_job: TvwJob | null; backup_at: string
}
export const getDebloat = (id: string) => api.get<TvwDebloat>(`${dev(id)}/debloat`)
export const readDebloat = (id: string) => api.post<{ job_id: string }>(`${dev(id)}/debloat/read`, {})
export const debloatOff = (id: string, packages: string[]) =>
  api.post<{ job_id: string }>(`${dev(id)}/debloat/off`, { confirm: true, packages })
export const debloatOn = (id: string, packages?: string[]) =>
  api.post<{ job_id: string }>(`${dev(id)}/debloat/on`, { confirm: true, packages: packages ?? null })
