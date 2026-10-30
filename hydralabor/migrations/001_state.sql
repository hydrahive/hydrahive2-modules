-- Hydra-Labor (hydralabor/PLAN-L1.md): ein Labor je Server, Zustand des Assistenten (eine Zeile, id = 1).
CREATE TABLE IF NOT EXISTS module_hydralabor_state (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    step          TEXT    NOT NULL DEFAULT 'start',
    running       TEXT    NOT NULL DEFAULT '',
    progress      TEXT    NOT NULL DEFAULT '',
    error_code    TEXT    NOT NULL DEFAULT '',
    error_step    TEXT    NOT NULL DEFAULT '',
    model         TEXT    NOT NULL DEFAULT '',
    cpu           INTEGER NOT NULL DEFAULT 2,
    ram_mb        INTEGER NOT NULL DEFAULT 4096,
    disk_gb       INTEGER NOT NULL DEFAULT 20,
    made          TEXT    NOT NULL DEFAULT '{}',
    last_net_ok   TEXT    NOT NULL DEFAULT '',
    last_test     TEXT    NOT NULL DEFAULT '{}',
    updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
