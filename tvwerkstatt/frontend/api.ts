import { api } from "@/shared/api-client"

export const BASE = "/modules/tvwerkstatt"

export interface TvwDevice {
  device_id: string; name: string; address: string; model?: string; android?: string; adb_state?: string
}
export interface TvwBuild {
  build_id: string; part: string; commit_id: string; sha256: string; state: string; created_at: string
}
export interface TvwState { incus: boolean; error_code: string; devices: TvwDevice[]; builds: TvwBuild[] }

export const getState = () => api.get<TvwState>(`${BASE}/state`)
