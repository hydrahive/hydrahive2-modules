export interface TelephonyFeatures {
  setup: boolean
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
  features: TelephonyFeatures
}

export type VoIPSection =
  | "overview"
  | "jobs"
  | "calls"
  | "archive"
  | "agent"
  | "settings"
  | "members"
