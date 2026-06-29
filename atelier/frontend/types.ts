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
