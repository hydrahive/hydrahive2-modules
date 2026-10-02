export type MediaKind = "audio" | "video"

export interface TrackMeta { prompt?: string; model?: string; duration?: number | string; created_at?: string }
export interface Track {
  id: number; title: string; size_bytes: number; uploaded_by: string; created_at: string
  media_kind: MediaKind; ext: string; meta: TrackMeta
}
export interface LibraryPermissions { can_upload: boolean; can_delete: boolean }
export interface TrackLibrary { tracks: Track[]; permissions: LibraryPermissions }
export interface ProjectSource {
  source: string; group: string; path: string; kind: MediaKind; title: string; meta: TrackMeta
  size_bytes: number; mtime: string; already_imported: boolean
}
