import { api } from "@/shared/api-client"
import type { AssistantSettings, CallEntry, Connection, ConnectionIn, DialStatus, TelephonyStatus } from "./types"

export const telephonyApi = {
  status: () => api.get<TelephonyStatus>("/modules/telephony/status"),
  connection: () => api.get<Connection>("/modules/telephony/connection"),
  saveConnection: (body: ConnectionIn) => api.put<Connection>("/modules/telephony/connection", body),
  connect: () => api.post<Connection>("/modules/telephony/connection/connect", {}),
  disconnect: () => api.post<Connection>("/modules/telephony/connection/disconnect", {}),
  deleteConnection: () => api.delete<void>("/modules/telephony/connection"),
  saveCalls: (body: { answer_calls: boolean; greeting: string } & Partial<AssistantSettings>) =>
    api.put<{ answer_calls: boolean; greeting: string }>("/modules/telephony/connection/calls", body),
  models: () => api.get<{ default: string; models: { id: string; label?: string }[] }>("/llm/models?modality=chat"),
  markRead: (id: number) => api.post<CallEntry>(`/modules/telephony/connection/calls/${id}/read`, {}),
  startTestCall: () => api.post<{ test_until: string; seconds: number }>("/modules/telephony/connection/test-call", {}),
  calls: () => api.get<{ calls: CallEntry[]; unread: number }>("/modules/telephony/connection/calls"),
  confirmHeard: (id: number, heard: boolean) =>
    api.post<CallEntry>(`/modules/telephony/connection/calls/${id}/heard`, { heard }),
  dial: (number: string, text: string) => api.post<DialStatus>("/modules/telephony/connection/dial", { number, text }),
  dialStatus: () => api.get<DialStatus>("/modules/telephony/connection/dial"),
  hangup: () => api.post<DialStatus>("/modules/telephony/connection/dial/hangup", {}),
  saveDialRules: (allow_premium: boolean, allow_foreign: boolean) =>
    api.put<{ allow_premium: boolean; allow_foreign: boolean }>("/modules/telephony/connection/dial-rules",
      { allow_premium, allow_foreign }),
}
