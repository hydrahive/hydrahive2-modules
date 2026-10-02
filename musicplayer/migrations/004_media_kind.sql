-- Audio- und Videoformate sowie optionale Anzeige-Metadaten.
-- Defaults halten alle bestehenden MP3-Tracks unverändert abspielbar.
ALTER TABLE module_musicplayer_tracks
ADD COLUMN media_kind TEXT NOT NULL DEFAULT 'audio';
ALTER TABLE module_musicplayer_tracks
ADD COLUMN ext TEXT NOT NULL DEFAULT 'mp3';
ALTER TABLE module_musicplayer_tracks
ADD COLUMN meta TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_musicplayer_tracks_project_kind_created
ON module_musicplayer_tracks(project_id, media_kind, created_at DESC);
