-- Radiostream Etappe 1: Bibliothek (radiostream/SPEC.md „Bauplan Etappe 1“).
-- Quelle: Adresse und NAME des Safe-Eintrags – nie das Passwort.
CREATE TABLE IF NOT EXISTS module_radiostream_sources (
    source_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    url TEXT NOT NULL,
    credential_name TEXT,
    state TEXT NOT NULL DEFAULT 'idle' CHECK(state IN ('idle','scanning','error')),
    last_scan_started TEXT,
    last_scan_finished TEXT,
    last_scan_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS module_radiostream_tracks (
    track_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    rel_path TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime INTEGER NOT NULL,
    artist TEXT NOT NULL DEFAULT '',
    album_artist TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    album TEXT NOT NULL DEFAULT '',
    genre TEXT NOT NULL DEFAULT '',
    year INTEGER,
    track_no INTEGER,
    duration_s REAL,
    bitrate INTEGER,
    sample_rate INTEGER,
    format TEXT NOT NULL,
    replaygain_db REAL,
    state TEXT NOT NULL DEFAULT 'ok' CHECK(state IN ('ok','missing','error')),
    error_code TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE(source_id, rel_path)
);
CREATE INDEX IF NOT EXISTS idx_radiostream_tracks_artist ON module_radiostream_tracks(artist);
CREATE INDEX IF NOT EXISTS idx_radiostream_tracks_genre ON module_radiostream_tracks(genre);
CREATE INDEX IF NOT EXISTS idx_radiostream_tracks_year ON module_radiostream_tracks(year);
CREATE INDEX IF NOT EXISTS idx_radiostream_tracks_state ON module_radiostream_tracks(state);

CREATE VIRTUAL TABLE IF NOT EXISTS module_radiostream_tracks_fts USING fts5(
    artist, title, album, genre,
    content='module_radiostream_tracks', content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS module_radiostream_tracks_ai AFTER INSERT ON module_radiostream_tracks BEGIN
    INSERT INTO module_radiostream_tracks_fts(rowid, artist, title, album, genre)
    VALUES (new.rowid, new.artist, new.title, new.album, new.genre);
END;
CREATE TRIGGER IF NOT EXISTS module_radiostream_tracks_ad AFTER DELETE ON module_radiostream_tracks BEGIN
    INSERT INTO module_radiostream_tracks_fts(module_radiostream_tracks_fts, rowid, artist, title, album, genre)
    VALUES ('delete', old.rowid, old.artist, old.title, old.album, old.genre);
END;
CREATE TRIGGER IF NOT EXISTS module_radiostream_tracks_au AFTER UPDATE ON module_radiostream_tracks BEGIN
    INSERT INTO module_radiostream_tracks_fts(module_radiostream_tracks_fts, rowid, artist, title, album, genre)
    VALUES ('delete', old.rowid, old.artist, old.title, old.album, old.genre);
    INSERT INTO module_radiostream_tracks_fts(rowid, artist, title, album, genre)
    VALUES (new.rowid, new.artist, new.title, new.album, new.genre);
END;

CREATE TABLE IF NOT EXISTS module_radiostream_scan_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    rel_path TEXT NOT NULL,
    code TEXT NOT NULL,
    at TEXT NOT NULL
);
