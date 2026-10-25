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
      answer_calls: boolean
      greeting: string
      greeting_default: string
      test_until: string | null
      call_mode: CallMode
      assistant_name: string
      assistant_knowledge: string
      assistant_model: string
      allow_premium: boolean
      allow_foreign: boolean
    })

export type CallMode = "greeting" | "assistant"

export interface CallNotes {
  name?: string
  callback_number?: string
  concern?: string
  callback_wanted?: boolean
  open_questions?: string[]
  needs_review?: boolean
  summary?: string
  result?: string
}

export interface AssistantSettings {
  mode: CallMode
  assistant_name: string
  assistant_knowledge: string
  assistant_model: string
}

export type CallResult =
  | "answered" | "rejected" | "busy" | "cancelled" | "caller_hangup" | "hung_up" | "no_ack" | "codec" | "no_port"
  | "assistant_end" | "no_input" | "max_duration" | "errors"
  | "no_answer" | "declined" | "invalid_number" | "failed" | "auth_failed" | "unreachable" | "remote_hangup"

export interface CallEntry {
  id: number
  started_at: string
  number: string
  result: CallResult
  codec: string
  rtp_out: number
  rtp_in: number
  is_test: boolean
  heard: boolean | null
  turns: number
  notes: CallNotes
  notes_read: boolean
  direction: "in" | "out"
}

export type DialMode = "greeting" | "assistant"

export interface DialRequest {
  number: string
  text: string
  mode: DialMode
  task: string
  may_share: string
}

/** Laufender bzw. letzter ausgehender Anruf (GET /connection/dial). */
export type DialStatus =
  | { active: false; state?: undefined }
  | { active: boolean; state: "calling" | "ringing" | "answered" | "ended"; number: string; result: string }
