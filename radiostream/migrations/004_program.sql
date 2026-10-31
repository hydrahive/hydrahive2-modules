-- Radiostream Etappe „Programm“ (PLAN-PROGRAMM.md): Playlisten, Mixe, Warteschlange, gewähltes Programm. Additiv.
CREATE TABLE IF NOT EXISTS module_radiostream_playlists (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    order_mode  TEXT NOT NULL DEFAULT 'ordered' CHECK (order_mode IN ('ordered','shuffle')),
    at_end      TEXT NOT NULL DEFAULT 'repeat' CHECK (at_end IN ('repeat','back')),
    created_by  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE IF NOT EXISTS module_radiostream_playlist_items (
    playlist_id TEXT NOT NULL,
    pos         INTEGER NOT NULL,
    track_id    TEXT NOT NULL,
    PRIMARY KEY (playlist_id, pos)
);
CREATE INDEX IF NOT EXISTS idx_radiostream_pl_items_track ON module_radiostream_playlist_items(track_id);
CREATE TABLE IF NOT EXISTS module_radiostream_mixes (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    rules       TEXT NOT NULL DEFAULT '{}',
    allow_long  INTEGER NOT NULL DEFAULT 0,
    created_by  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE IF NOT EXISTS module_radiostream_queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pos         INTEGER NOT NULL,
    track_id    TEXT NOT NULL,
    added_by    TEXT NOT NULL DEFAULT '',
    added_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
-- Gewähltes Programm (eine Zeile). cursor = nächste Stelle der Playlist (der Reihe nach), played = schon gespielte
-- Stellen bei „gemischt“ (JSON-Liste), damit kein Titel doppelt kommt, bevor alle liefen.
CREATE TABLE IF NOT EXISTS module_radiostream_program (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    mode        TEXT NOT NULL DEFAULT 'all' CHECK (mode IN ('all','playlist','mix')),
    ref_id      TEXT NOT NULL DEFAULT '',
    cursor      INTEGER NOT NULL DEFAULT 0,
    played      TEXT NOT NULL DEFAULT '[]',
    notice      TEXT NOT NULL DEFAULT '',
    updated_by  TEXT NOT NULL DEFAULT '',
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
-- „Ausgeschlossen von Alles“ (JSON: genres, genre_parts, folders) und lange Titel in Alles/Mixen. NULL = Voreinstellung.
ALTER TABLE module_radiostream_station ADD COLUMN exclude_rules TEXT;
ALTER TABLE module_radiostream_station ADD COLUMN allow_long INTEGER NOT NULL DEFAULT 0;
-- Herkunft je gespieltem Titel (Warteschlange, Playlist-Stelle, Mix), damit ein vorgeladener Titel bei einer
-- Programmänderung sauber zurückgenommen werden kann (autodj.flush).
ALTER TABLE module_radiostream_plays ADD COLUMN source TEXT NOT NULL DEFAULT '';
ALTER TABLE module_radiostream_plays ADD COLUMN ref TEXT NOT NULL DEFAULT '';
