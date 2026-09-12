-- Musicplayer-Tracks einem Projektworkspace zuordnen.
-- Uneindeutige Legacy-Zeilen bleiben NULL und werden über die Projekt-API nie sichtbar.
ALTER TABLE module_musicplayer_tracks ADD COLUMN project_id TEXT;

UPDATE module_musicplayer_tracks
SET project_id = substr(
    source,
    10,
    instr(substr(source, 10), '/') - 1
)
WHERE source LIKE 'projects/%/%'
  AND instr(substr(source, 10), '/') > 1;

CREATE INDEX IF NOT EXISTS idx_musicplayer_tracks_project_created
ON module_musicplayer_tracks(project_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_musicplayer_tracks_project_source
ON module_musicplayer_tracks(project_id, source)
WHERE source IS NOT NULL AND source != '';
