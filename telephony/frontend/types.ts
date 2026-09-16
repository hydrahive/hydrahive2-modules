export interface TelephonyFeatures {
  setup: boolean
  registration_probe: boolean
  inbound_calls: boolean
  outbound_calls: boolean
  archive: boolean
}

export interface TelephonyStatus {
  module: "telephony"
  stage: "foundation"
  status: "not_configured"
  configured: false
  telephony_available: false
  probe_target: {
    registrar: string
    port: number
  }
  features: TelephonyFeatures
}

export type RegistrationProbeOutcome =
  | "registered"
  | "auth_failed"
  | "registration_failed"
  | "timeout"
  | "runtime_unavailable"
  | "busy"

export interface RegistrationProbeRequest {
  registrar: string
  port: number
  username: string
  password: string
}

export interface RegistrationProbeResponse {
  outcome: RegistrationProbeOutcome
}

export type VoIPSection =
  | "overview"
  | "jobs"
  | "calls"
  | "archive"
  | "agent"
  | "settings"
  | "members"
