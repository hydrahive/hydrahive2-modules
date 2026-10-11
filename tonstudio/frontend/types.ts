// Typen passend zu backend/song_model.py (Format hydrahive.song v1) und backend/providers/_base.py.

export interface SongSummary {
  id: string
  title: string
  version: number
  bpm: number | null
  key: string | null
  tracks: number
  updated_at: string
  created_at: string
}

export interface Clip {
  id: string
  source_rel: string
  t_start: number
  src_start: number
  src_end: number
  gain_db: number
  fade_in: number
  fade_out: number
}

export interface Track {
  id: string
  name: string
  role: "full" | "vocals" | "drums" | "bass" | "other" | "fx" | "guide"
  gain_db: number
  pan: number
  mute: boolean
  solo: boolean
  clips: Clip[]
}

export interface Song {
  format: "hydrahive.song"
  format_version: 1
  id: string
  version: number
  title: string
  bpm: number | null
  key: string | null
  time_signature: string
  sections: unknown[]
  tracks: Track[]
  master: { gain_db: number; loudness_lufs: number }
  lyrics: { ref: unknown }
  score: { ref: unknown }
  created_at: string
  updated_at: string
}

export interface LibraryItem {
  source_rel: string
  origin: "generated" | "upload" | "project"
  name: string
  duration: number | null
  model: string | null
  backend: string | null
  prompt: string | null
  created_at: string | null
  size_bytes?: number
}

export interface MusicModel {
  id: string
  name: string
  backend: string
  lyrics: boolean
  image_ref: boolean
  audio_ref: boolean
  instrumental_switch: boolean
  max_seconds: number | null
  local: boolean
  price_note: string
  license_note: string
  notes: string[]
}

export interface MusicRequest {
  style: string
  description: string
  bpm: number | null
  key: string | null
  duration_s: number | null
  instrumental: boolean
  lyrics: string
}

export interface GenerateResult extends LibraryItem {
  returned_text: string
  price_note: string
}
