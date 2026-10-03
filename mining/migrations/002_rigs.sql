-- Mining-Modul E2: Rechner (Rigs) und Kopplungs-Codes.
-- Tokens und Codes nur als SHA-256, nie im Klartext.

CREATE TABLE IF NOT EXISTS module_mining_rigs (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    status          TEXT NOT NULL DEFAULT 'pending',   -- pending | active | revoked
    token_hash      TEXT UNIQUE,                        -- NULL = gesperrt
    enabled         INTEGER NOT NULL DEFAULT 1,         -- Admin-Schalter an/aus
    follows_power   INTEGER NOT NULL DEFAULT 1,         -- E5 Energie-Steuerung
    priority        INTEGER NOT NULL DEFAULT 0,
    hostname        TEXT,
    os              TEXT,
    client_version  TEXT,
    gpu_vendor      TEXT,
    gpu_model       TEXT,
    gpu_mem_mb      INTEGER,
    driver          TEXT,
    remote_ip       TEXT,
    last_report     TEXT,                               -- letzte Meldung (JSON, begrenzt)
    last_seen       TEXT,
    created_at      TEXT NOT NULL,
    approved_at     TEXT
);

CREATE TABLE IF NOT EXISTS module_mining_pairing (
    code_hash   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    used_at     TEXT,
    created_by  TEXT,
    created_at  TEXT NOT NULL
);
