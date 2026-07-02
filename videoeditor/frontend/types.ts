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

export interface EDL {
  file_id: string
  timeline: Clip[]
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
