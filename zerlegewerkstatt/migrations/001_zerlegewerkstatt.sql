CREATE TABLE IF NOT EXISTS module_zerlege_cases (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    title TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '',
    question TEXT NOT NULL,
    purpose TEXT NOT NULL,
    authorized INTEGER NOT NULL CHECK (authorized = 1),
    authorization_note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    error_code TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_module_zerlege_cases_project
    ON module_zerlege_cases (project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS module_zerlege_artifacts (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES module_zerlege_cases(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    kind TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (case_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_module_zerlege_artifacts_case
    ON module_zerlege_artifacts (case_id, created_at);

CREATE TABLE IF NOT EXISTS module_zerlege_jobs (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES module_zerlege_cases(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES module_zerlege_artifacts(id) ON DELETE CASCADE,
    analysis_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    result_path TEXT,
    log_path TEXT,
    error_code TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_module_zerlege_jobs_case
    ON module_zerlege_jobs (case_id, created_at DESC);
