-- Hydra-Labor L2 (PLAN-L2.md): GitHub-Verbindung (eine Zeile, Token verschlüsselt) und Einreichungen.
CREATE TABLE IF NOT EXISTS module_hydralabor_github (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    token_enc     TEXT    NOT NULL DEFAULT '',
    login         TEXT    NOT NULL DEFAULT '',
    user_id       INTEGER NOT NULL DEFAULT 0,
    scopes        TEXT    NOT NULL DEFAULT '',
    connected_at  TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS module_hydralabor_submissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kind          TEXT    NOT NULL,              -- pr | issue
    target        TEXT    NOT NULL,              -- core | modules
    title         TEXT    NOT NULL,
    branch        TEXT    NOT NULL DEFAULT '',
    number        INTEGER NOT NULL DEFAULT 0,
    url           TEXT    NOT NULL DEFAULT '',
    state         TEXT    NOT NULL DEFAULT 'submitted',   -- submitted | merged | closed
    note          TEXT    NOT NULL DEFAULT '',
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
