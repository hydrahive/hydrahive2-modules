import { api } from "@/shared/api-client"

export const BASE = "/modules/tvwerkstatt"

export interface TvwDevice {
  device_id: string; name: string; address: string; model?: string; android?: string; adb_state?: string
}
export interface TvwBuild {
  build_id: string; part: string; commit_id: string; sha256: string; state: string; created_at: string
}
export interface TvwJob {
  job_id: string; state: "running" | "done" | "failed" | string; step: string; error_code: string
  error_detail: string; started_by: string; created_at: string; updated_at: string
}
export type ContainerState = "missing" | "stopped" | "running" | "unknown"
export interface TvwState {
  incus: boolean; error_code: string; devices: TvwDevice[]; builds: TvwBuild[]
  container: ContainerState; setup: TvwJob | null
}

export const getState = () => api.get<TvwState>(`${BASE}/state`)
export const startSetup = (acceptLicense: boolean) =>
  api.post<{ job_id: string }>(`${BASE}/setup`, { accept_license: acceptLicense })
export const stopContainer = () => api.post<{ container: ContainerState }>(`${BASE}/container/stop`, {})
export const removeContainer = () => api.delete<{ container: ContainerState }>(`${BASE}/container`)
