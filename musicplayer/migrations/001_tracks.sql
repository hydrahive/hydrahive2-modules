-- Musicplayer — hochgeladene MP3-Tracks (gemeinsamer Pool). Additiv, IF NOT EXISTS.
-- filename: UUID-Speichername auf der Platte (kein Original-Name → keine Traversal).
-- title: Anzeigename (Upload-Feld oder bereinigter Original-Dateiname).
CREATE TABLE IF NOT EXISTS module_musicplayer_tracks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    filename    TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    uploaded_by TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_musicplayer_tracks_created
    ON module_musicplayer_tracks(created_at DESC);
