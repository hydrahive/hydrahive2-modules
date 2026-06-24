// Musicplayer — Typen.

export interface Track {
  id: number
  title: string
  size_bytes: number
  uploaded_by: string
  created_at: string
}

export interface GeneratedTrack {
  path: string
  workspace: string
  size_bytes: number
  mtime: string
  already_imported: boolean
}
