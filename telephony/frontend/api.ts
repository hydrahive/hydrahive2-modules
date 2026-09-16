import { api } from "@/shared/api-client"
import type {
  RegistrationProbeRequest,
  RegistrationProbeResponse,
  TelephonyStatus,
} from "./types"

export const telephonyApi = {
  status: () => api.get<TelephonyStatus>("/modules/telephony/status"),
  testRegistration: (body: RegistrationProbeRequest) =>
    api.post<RegistrationProbeResponse>(
      "/modules/telephony/spike/registration-test",
      body,
    ),
}
