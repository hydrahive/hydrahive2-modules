// Musicplayer — projektgebundene API-Typen.

export interface Track {
  id: number
  title: string
  size_bytes: number
  uploaded_by: string
  created_at: string
}

export interface LibraryPermissions {
  can_upload: boolean
  can_delete: boolean
}

export interface TrackLibrary {
  tracks: Track[]
  permissions: LibraryPermissions
}

export interface GeneratedTrack {
  path: string
  workspace: string
  size_bytes: number
  mtime: string
  already_imported: boolean
}
