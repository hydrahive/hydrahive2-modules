-- Diagramme (Spec §5a): jedes erstellte Diagramm bleibt gespeichert. Ändern = neue Fassung (version_of),
-- Löschen = Papierkorb (deleted_at). Dateien liegen unter data_dir/diagramme/<id>/.
CREATE TABLE IF NOT EXISTS module_diagrams (
    id          TEXT PRIMARY KEY,
    username    TEXT NOT NULL,
    project_id  TEXT,
    session_id  TEXT,
    agent_id    TEXT,
    title       TEXT NOT NULL,
    kind        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    version_of  TEXT,
    deleted_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_module_diagrams_user ON module_diagrams (username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_module_diagrams_project ON module_diagrams (project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_module_diagrams_version ON module_diagrams (version_of);
