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
