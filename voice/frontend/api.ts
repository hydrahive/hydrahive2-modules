import { api } from "@/shared/api-client"
import type {
  LlmModelsResponse, LlmState, SettingsResponse, SttInfo, TranscriptResponse,
  VoiceSettings, VoiceStatus,
} from "./types"

const BASE = "/modules/voice"

export const voiceApi = {
  status: () => api.get<VoiceStatus>(`${BASE}/status`),
  getSettings: () => api.get<SettingsResponse>(`${BASE}/settings`),
  putSettings: (patch: Partial<VoiceSettings>) =>
    api.put<SettingsResponse>(`${BASE}/settings`, patch),
  transcript: (since = 0, limit = 50) =>
    api.get<TranscriptResponse>(`${BASE}/transcript?since=${since}&limit=${limit}`),
  say: (text: string) => api.post<{ accepted: boolean }>(`${BASE}/say`, { text }),
  getLlm: () => api.get<LlmState>(`${BASE}/llm`),
  putLlm: (model: string | null) => api.put<LlmState>(`${BASE}/llm`, { model }),
  llmModels: () => api.get<LlmModelsResponse>(`${BASE}/llm/models`),
  stt: () => api.get<SttInfo>(`${BASE}/stt`),
}
