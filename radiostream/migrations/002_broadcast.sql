-- Radiostream Etappe 2: Sendebetrieb (radiostream/PLAN-E2.md). Additiv, IF NOT EXISTS.
-- Gespielt-Liste für die Rotation (Sperren je Künstler/Titel) und „zuletzt gespielt“. 30 Tage aufbewahrt.
CREATE TABLE IF NOT EXISTS module_radiostream_plays (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id   TEXT NOT NULL,
    artist_key TEXT NOT NULL,
    played_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_radiostream_plays_at ON module_radiostream_plays(played_at);
CREATE INDEX IF NOT EXISTS idx_radiostream_plays_track ON module_radiostream_plays(track_id);
CREATE INDEX IF NOT EXISTS idx_radiostream_plays_artist ON module_radiostream_plays(artist_key);

-- Sender-Einstellungen (eine Zeile). Alles über die Oberfläche einstellbar (Till 29.10.).
CREATE TABLE IF NOT EXISTS module_radiostream_station (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    name             TEXT    NOT NULL DEFAULT 'Radiostream',
    subtitle         TEXT    NOT NULL DEFAULT '',
    artist_gap_min   INTEGER NOT NULL DEFAULT 60,
    title_gap_days   INTEGER NOT NULL DEFAULT 3,
    listen_port      INTEGER NOT NULL DEFAULT 8800,
    reach            TEXT    NOT NULL DEFAULT 'all' CHECK (reach IN ('all','home','off')),
    max_listeners    INTEGER NOT NULL DEFAULT 50,
    updated_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_by       TEXT    NOT NULL DEFAULT ''
);
