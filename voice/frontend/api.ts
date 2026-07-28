import { api } from "@/shared/api-client"
import type { SettingsResponse, VoiceSettings, VoiceStatus } from "./types"

const BASE = "/modules/voice"

export const voiceApi = {
  status: () => api.get<VoiceStatus>(`${BASE}/status`),
  getSettings: () => api.get<SettingsResponse>(`${BASE}/settings`),
  putSettings: (patch: Partial<VoiceSettings>) =>
    api.put<SettingsResponse>(`${BASE}/settings`, patch),
}
