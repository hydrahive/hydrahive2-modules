import { api } from "@/shared/api-client"
import type { TelephonyStatus } from "./types"

export const telephonyApi = {
  status: () => api.get<TelephonyStatus>("/modules/telephony/status"),
}
