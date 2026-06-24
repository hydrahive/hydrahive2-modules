-- Quelle eines Tracks: relativer Pfad unter workspaces/ bei Import generierter
-- Musik (R2b), leer bei normalem Upload. Dient dem Dedup beim Import.
-- Das Migrations-System toleriert "duplicate column name" (idempotent genug).
ALTER TABLE module_musicplayer_tracks ADD COLUMN source TEXT NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_musicplayer_tracks_source
    ON module_musicplayer_tracks(source);
