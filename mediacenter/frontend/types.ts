export type MediaType = "movie" | "tv" | "book" | "audiobook" | "audioplay" | "music"
export type View = "search" | "queue" | "history"
export type SelectionStatus = "ready" | "quality_preference_required" | "format_preference_required"

export interface ModuleStatus {
  module: "mediacenter"
  state: "ready" | "not_configured"
  indexer_configured: boolean
  sab_configured: boolean
}

export interface ConnectionTest {
  ok: boolean
  max_limit: number
  default_limit: number
  search_types: string[]
  categories: number[]
  sab_version: string | null
  sab_categories: string[]
}

export interface SearchFilters {
  query: string
  media_type: MediaType
  limit?: number
  year?: number
  season?: number
  episode?: string
  author?: string
  artist?: string
  album?: string
  max_age_days?: number
  min_size_mb?: number
  max_size_mb?: number
}

export interface SearchResult {
  result_id: string | null
  title: string
  media_type: MediaType
  category_id: number
  size_bytes: number | null
  age_days: number | null
  decision: "eligible" | "rejected"
  reasons: string[]
  language: string | null
  resolution: string | null
  format: string | null
  bitrate_kbps: number | null
  score: number
  selection_status: SelectionStatus
  meta: ReleaseMeta | null
}

/** Anzeige-Metadaten aus den Newznab-Attributen. Alle Felder optional. */
export interface ReleaseMeta {
  cover_url: string | null
  backdrop_url: string | null
  title_clean: string | null
  year: number | null
  score: number | null
  genres: string[]
  plot: string | null
  imdb_id: string | null
  tmdb_id: string | null
  tvdb_id: string | null
  season: number | null
  episode: number | null
  artist: string | null
  album: string | null
  label: string | null
}

/** Ein Titel mit allen gefundenen Fassungen — die Karte im Poster-Raster. */
export interface ResultGroup {
  key: string
  title: string
  year: number | null
  cover_url: string | null
  backdrop_url: string | null
  rating: number | null
  genres: string[]
  plot: string | null
  media_type: MediaType
  releases: SearchResult[]
}

/** Was der Server aus der freien Eingabe gelesen hat — Basis der Chips. */
export interface InterpretedQuery {
  query: string
  recognized: string[]
  year: number | null
  season: number | null
  episode: string | null
  language: string | null
  resolution: number | null
  audio_format: string | null
}

export interface SearchResponse {
  total: number
  eligible: number
  results: SearchResult[]
  groups: ResultGroup[]
  interpreted: InterpretedQuery | null
}

export interface EnqueueResponse {
  result_id: string
  title: string
  media_type: MediaType
  state: string
  sab_job_id: string | null
  error_code: string | null
}

export interface Job {
  result_id: string
  title: string
  media_type: MediaType
  state: string
  sab_job_id: string | null
  status: string
  progress: number | null
  eta: string | null
  speed_kbps: number | null
  error_code: string | null
  updated_at: string
}
