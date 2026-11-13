import { api } from "@/shared/api-client"

export const BASE = "/modules/tvwerkstatt"

export interface TvwDevice {
  device_id: string; name: string; address: string; adb_port?: number; model?: string; android?: string
  sdk?: number; kind?: string; stock_home?: string; current_home?: string; adb_state?: string; checked_at?: string
  check?: TvwJob | null
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
