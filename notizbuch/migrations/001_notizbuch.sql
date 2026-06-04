CREATE TABLE IF NOT EXISTS module_notizbuch_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_module_notizbuch_notes_user ON module_notizbuch_notes("user");
