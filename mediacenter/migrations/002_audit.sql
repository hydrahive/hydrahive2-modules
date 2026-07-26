ALTER TABLE module_mediacenter_jobs ADD COLUMN agent_id TEXT;
ALTER TABLE module_mediacenter_jobs ADD COLUMN session_id TEXT;
ALTER TABLE module_mediacenter_jobs ADD COLUMN profile_summary TEXT NOT NULL DEFAULT '{}';

CREATE TABLE module_mediacenter_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner TEXT NOT NULL,
    agent_id TEXT,
    session_id TEXT,
    action TEXT NOT NULL,
    media_type TEXT NOT NULL,
    result_hash TEXT NOT NULL,
    title TEXT NOT NULL,
    sab_job_id TEXT,
    state TEXT NOT NULL,
    error_code TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_mediacenter_audit_owner_created
    ON module_mediacenter_audit(owner, created_at DESC);
