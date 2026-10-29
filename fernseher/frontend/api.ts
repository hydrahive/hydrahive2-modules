import { api } from "@/shared/api-client"
import { BASE } from "./logic"

export interface TvChannel { number: number | null; name: string }
export interface TvStatus {
  power: "on" | "standby"; channel: TvChannel | null; program: string; volume: number; muted: boolean; model: string
}
export interface TvSettings { configured: boolean; name: string; address: string; psk_set: boolean; volume_limit: number }

export const getSettings = () => api.get<TvSettings>(`${BASE}/settings`)
export const saveSettings = (s: { name: string; address: string; psk: string; volume_limit: number }) =>
  api.put<TvSettings>(`${BASE}/settings`, { ...s, psk: s.psk.trim() || null })
export const testConnection = () => api.post<{ ok: boolean; model: string; power: string }>(`${BASE}/test`, {})
export const getStatus = () => api.get<TvStatus>(`${BASE}/status`)
export const getChannels = () => api.get<{ number: number; name: string }[]>(`${BASE}/channels`)
export const getApps = () => api.get<{ name: string }[]>(`${BASE}/apps`)
export const setChannel = (sender: string) => api.post<TvStatus>(`${BASE}/channel`, { sender })
export const setVolume = (wert: string) => api.post<TvStatus>(`${BASE}/volume`, { wert })
export const setMute = (stumm: boolean) => api.post<TvStatus>(`${BASE}/mute`, { stumm })
export const setPower = (an: boolean) => api.post<TvStatus>(`${BASE}/power`, { an })
export const startApp = (name: string) => api.post<{ started: string }>(`${BASE}/app`, { name })
