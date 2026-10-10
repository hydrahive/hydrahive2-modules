-- Kopplungs-Codes (nur Hash) und gekoppelte Brillen.
CREATE TABLE IF NOT EXISTS module_vr_pairing (
    code_hash   TEXT PRIMARY KEY,
    username    TEXT NOT NULL,
    name        TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    used_at     TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_module_vr_pairing_user ON module_vr_pairing (username);

CREATE TABLE IF NOT EXISTS module_vr_headsets (
    id         TEXT PRIMARY KEY,
    username   TEXT NOT NULL,
    name       TEXT NOT NULL,
    key_id     TEXT NOT NULL,
    paired_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_module_vr_headsets_user ON module_vr_headsets (username);
