export interface AtelierCharacter {
  id: string
  name: string
  description: string
  style_anchor: string
  palette: string[]
  seed: number | null
  model: string
  references: string[]
}

export interface AtelierCI {
  palette: string[]
  style_anchor: string
  default_model: string
  aspect_ratio: string
}

export interface GalleryItem {
  name: string
  path: string
  rel: string
  created_at: string | null
  prompt: string | null
  seed: number | null
  model: string | null
  mtime: number
}

export interface GenerateRequest {
  scene: string
  character_ids: string[]
  model?: string
  seed?: number | null
  aspect_ratio?: string
  camera?: Record<string, string>
  style?: string
}

/** {group: [keys]} — Regie-Preset-Katalog vom Backend. */
export type PresetCatalog = Record<string, string[]>

export interface VideoJob {
  job_id: string
  status: "pending" | "processing" | "completed" | "failed"
  source_rel: string
  prompt: string
  model: string
  duration: number
  aspect_ratio: string
  video_rel: string | null
  error: string | null
  created_at: string
}

export interface VideoRequest {
  source_rel: string
  prompt: string
  model?: string
  duration?: number
  aspect_ratio?: string
}

export interface FilmJob {
  job_id: string
  status: "pending" | "processing" | "completed" | "failed"
  clips: string[]
  resolution: string
  music_rel: string
  film_rel: string | null
  error: string | null
  created_at: string
}

export interface GenerateResult {
  name: string
  rel: string
  path: string
  prompt: string
  seed: number | null
  model: string
  created_at: string
}

export type CharacterInput = Omit<AtelierCharacter, "id" | "references">

// ---------------------------------------------------------------- Audio (Musik)
export interface AudioProfile {
  id: string
  name: string
  description: string
  model: string
}

export type AudioProfileInput = Omit<AudioProfile, "id">

export interface AudioLibraryItem {
  name: string
  rel: string
  created_at: string | null
  prompt: string | null
  model: string | null
  profile_ids: string[]
  mtime: number
}

export interface MusicGenerateRequest {
  scene: string
  profile_ids: string[]
  model?: string
}

export interface MusicGenerateResult {
  name: string
  rel: string
  path: string
  prompt: string
  model: string
  created_at: string
}

// ---------------------------------------------------------------- Regie (Screenplay)
export interface Screenplay {
  title: string
  logline: string
  description: string
  film_model: string
  audio_model: string
  voice_model: string
  aspect_ratio: string
  default_duration: number
  scene_order: string[]
  created_at?: string
  updated_at?: string
}

export interface SceneDialogue {
  character_id: string
  line: string
  emotion: string
}

export interface SceneMusic {
  enabled: boolean
  prompt: string
  music_rel: string | null
}

export interface Scene {
  id: string
  title: string
  description: string
  character_ids: string[]
  dialogues: SceneDialogue[]
  music: SceneMusic
  camera: Record<string, string>
  location: string
  time_of_day: string
  created_at?: string
  updated_at?: string
}

export type SceneInput = Omit<Scene, "id" | "created_at" | "updated_at">

export interface MediaModel {
  id: string
  name: string
}

export interface MediaModelList {
  default: string
  models: MediaModel[]
}
