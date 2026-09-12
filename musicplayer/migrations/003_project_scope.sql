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

-- Ältere Imports aus dem Master-Workspace tragen keine Projekt-ID. Wenn alle
-- bereits eindeutig zuordenbaren Imports desselben Uploaders genau auf EIN
-- Projekt zeigen, ist diese Zuordnung deterministisch. Bei mehreren Projekten
-- bleiben die Tracks bewusst unzugeordnet statt im falschen Projekt zu landen.
UPDATE module_musicplayer_tracks
SET project_id = (
    SELECT MIN(known.project_id)
    FROM module_musicplayer_tracks AS known
    WHERE known.uploaded_by = module_musicplayer_tracks.uploaded_by
      AND known.project_id IS NOT NULL
)
WHERE project_id IS NULL
  AND source LIKE 'master/%/%'
  AND (
      SELECT COUNT(DISTINCT known.project_id)
      FROM module_musicplayer_tracks AS known
      WHERE known.uploaded_by = module_musicplayer_tracks.uploaded_by
        AND known.project_id IS NOT NULL
  ) = 1;

CREATE INDEX IF NOT EXISTS idx_musicplayer_tracks_project_created
ON module_musicplayer_tracks(project_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_musicplayer_tracks_project_source
ON module_musicplayer_tracks(project_id, source)
WHERE source IS NOT NULL AND source != '';
