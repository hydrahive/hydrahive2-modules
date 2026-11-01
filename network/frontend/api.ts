import { api } from "@/shared/api-client"
import { BASE, type Outage, type Sample, type Speedtest } from "./logic"

export interface UdmStatus { wan_status: string | null; isp: string | null; availability: number | null; latency_ms: number | null; drops: number | null }
export interface Overview {
  configured: boolean; latest: Sample | null; udm: UdmStatus | null; udm_at: number | null; udm_error: string | null
  udm_confirmed: boolean; fritz: boolean; plan: { down: number | null; up: number | null }; last_speedtest: Speedtest | null
}
export interface Settings {
  udm_url: string | null; udm_credential: string | null; udm_pin: string | null; fritz_host: string | null
  fritz_credential: string | null; plan_down_mbit: number | null; plan_up_mbit: number | null; plan_price_eur: number | null
  last_full_sync: number | null; last_error: string | null
}
export type SettingsIn = {
  udm_url: string; udm_credential: string; fritz_host: string; fritz_credential: string
  plan_down_mbit: number | null; plan_up_mbit: number | null; plan_price_eur: number | null
}
export interface Outages { items: Outage[]; per_day: Record<string, number>; per_day_cable: Record<string, number>; per_day_internet: Record<string, number> }
export interface Cred { name: string; type: string; url_pattern: string }

export const getOverview = () => api.get<Overview>(`${BASE}/overview`)
export const getSamples = (hours: number) => api.get<{ items: Sample[] }>(`${BASE}/samples?hours=${hours}`)
export const getOutages = (days: number) => api.get<Outages>(`${BASE}/outages?days=${days}`)
export const getSpeedtests = (days: number) => api.get<{ items: Speedtest[] }>(`${BASE}/speedtests?days=${days}`)
export const getSettings = () => api.get<Settings>(`${BASE}/settings`)
export const saveSettings = (v: SettingsIn) => api.put<Settings>(`${BASE}/settings`, v)
export const getCreds = () => api.get<{ items: Cred[] }>(`${BASE}/credentials`)
export const fetchFingerprint = () => api.post<{ fingerprint: string; pretty: string }>(`${BASE}/udm/fingerprint`, {})
export const confirmFingerprint = (fingerprint: string) => api.post<Settings>(`${BASE}/udm/confirm`, { fingerprint })
export const testUdm = () => api.post<{ ok: boolean; version: string | null }>(`${BASE}/udm/test`, {})
export const syncNow = () => api.post<{ events: number; speedtests: number }>(`${BASE}/sync`, {})
export const importSnapshot = (file: File) => {
  const f = new FormData()
  f.append("file", file)
  return api.postForm<{ events: number; speedtests: number; hour: number }>(`${BASE}/import`, f)
}
