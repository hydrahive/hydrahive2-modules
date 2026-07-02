export type ClipMode = "copy" | "reencode"

export interface Clip {
  id: string
  src_start: number
  src_end: number
  mode: ClipMode
}

export interface SpriteMeta {
  count: number
  cols: number
  rows: number
  tile_w: number
  tile_h: number
  interval: number
}

export interface AudioClip {
  id: string
  source_rel: string
  t_start: number      // Position auf der Timeline (s)
  src_start: number    // Ausschnitt-Anfang in der Quelle (s)
  src_end: number      // Ausschnitt-Ende in der Quelle (s)
  gain_db: number
  fade_in: number
  fade_out: number
}

export interface AudioTrack {
  id: string
  name: string
  mute: boolean
  solo: boolean
  gain_db: number
  clips: AudioClip[]
}

export interface OriginalAudio {
  mute: boolean
  gain_db: number
}

export interface EDL {
  file_id: string
  timeline: Clip[]
  original_audio?: OriginalAudio
  audio?: AudioTrack[]
}

/** Aufbereitete Audiodatei — Sidecar-Meta (Dauer + Peaks-Verweis). */
export interface AudioMeta {
  audio_id: string
  filename: string
  source_rel: string
  duration: number
  sample_rate: number
  channels: number
  peaks_abs?: string
}

/** Normalisierte Wellenform: min in [-1,0], max in [0,1], pro Sekunde `peaks_per_second` Werte. */
export interface AudioPeaks {
  peaks_per_second: number
  duration: number
  min: number[]
  max: number[]
}

export interface AudioBrowseEntry {
  source_rel: string
  filename: string
  audio_id: string
  prepared: boolean
  size_bytes: number
}

export interface VideoMeta {
  file_id: string
  filename: string
  source_rel: string
  duration: number
  fps: number
  width: number
  height: number
  has_audio: boolean
  keyframes: number[]
  sprite: SpriteMeta | null
  edl: EDL | null
  proxy_abs?: string
  sprite_abs?: string
}

export interface BrowseEntry {
  source_rel: string
  filename: string
  file_id: string
  imported: boolean
  size_bytes: number
}

export interface Job {
  job_id: string
  kind: "proxy" | "export" | "import"
  file_id: string
  status: "running" | "done" | "failed"
  percent?: number
  error: string | null
  created_at: string
  finished_at: string | null
}

export interface RenderPreset {
  id: string
  title: string
  note: string
  profile: Record<string, unknown>
}

export interface UploadResult {
  file_id: string
  job_id: string
}

export interface ExportResult {
  export_id: string
  job_id: string
}
