export type VoiceStatus = {
  module: string
  stage: string
  bridge: "up" | "down"
  device: "connected" | "disconnected"
}

export type WakeSensitivity =
  | "Slightly sensitive"
  | "Moderately sensitive"
  | "Very sensitive"

export type VoiceSettings = {
  volume: number
  mute: boolean
  wake_sound: boolean
  wake_word_sensitivity: WakeSensitivity | ""
  led_on: boolean
  led_brightness: number
}

export type SettingsResponse = {
  bridge: "up" | "down"
  device?: "connected" | "disconnected"
  settings: VoiceSettings | null
}

export const WAKE_SENSITIVITIES: WakeSensitivity[] = [
  "Slightly sensitive",
  "Moderately sensitive",
  "Very sensitive",
]

export type TranscriptTurn = {
  id: number
  ts: number
  role: "user" | "assistant"
  kind: "speech" | "media" | "error"
  text: string
}

export type TranscriptResponse = {
  bridge: "up" | "down"
  turns: TranscriptTurn[]
  cursor: number
}

export type LlmState = {
  override: string | null
  agent_default: string
  has_session: boolean
}

export type LlmModel = { id: string; label: string; provider: string }

export type LlmModelsResponse = {
  agent_default: string
  models: LlmModel[]
}
