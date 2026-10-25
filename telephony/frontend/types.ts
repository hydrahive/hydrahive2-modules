export interface TelephonyFeatures {
  setup: boolean
  registration: boolean
  inbound_calls: boolean
  outbound_calls: boolean
  archive: boolean
}

export interface TelephonyStatus {
  module: "telephony"
  stage: "connection"
  status: ConnectionStatus
  configured: boolean
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

export type Pbx = "fritzbox" | "sip"

export type ConnectionStatus =
  | "not_configured"
  | "disconnected"
  | "connecting"
  | "registered"
  | "auth_failed"
  | "not_found"
  | "unreachable"
  | "rejected"
  | "blocked"
  | "port_in_use"
  | "secret_invalid"

export interface ConnectionFields {
  pbx: Pbx
  display_name: string
  registrar: string
  registrar_port: number
  username: string
  own_number: string
  local_sip_port: number
  rtp_port_min: number
  rtp_port_max: number
  register_interval: number
}

/** PUT-Body: Kennwort leer = beim Ändern unverändert. */
export interface ConnectionIn extends ConnectionFields {
  password: string
}

export type Connection =
  | { configured: false; status: "not_configured" }
  | (ConnectionFields & {
      configured: true
      has_password: true
      enabled: boolean
      status: ConnectionStatus
      status_at: string | null
      created_at: string
      updated_at: string
    })
