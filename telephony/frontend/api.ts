import { api } from "@/shared/api-client"
import type { Connection, ConnectionIn, TelephonyStatus } from "./types"

export const telephonyApi = {
  status: () => api.get<TelephonyStatus>("/modules/telephony/status"),
  connection: () => api.get<Connection>("/modules/telephony/connection"),
  saveConnection: (body: ConnectionIn) => api.put<Connection>("/modules/telephony/connection", body),
  connect: () => api.post<Connection>("/modules/telephony/connection/connect", {}),
  disconnect: () => api.post<Connection>("/modules/telephony/connection/disconnect", {}),
  deleteConnection: () => api.delete<void>("/modules/telephony/connection"),
}
