CREATE TABLE IF NOT EXISTS module_opentor_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO module_opentor_config (key, value) VALUES
    ('enabled', '0'),
    ('max_chars', '8000'),
    ('retention_days', '30'),
    ('allowed_modes', '["threat_intel","ransomware","corporate"]');

CREATE TABLE IF NOT EXISTS module_opentor_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id TEXT NOT NULL,
    project_id TEXT,
    kind TEXT NOT NULL,
    source_url TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_module_opentor_evidence_owner
    ON module_opentor_evidence(owner_id, project_id, created_at);
