CREATE TABLE IF NOT EXISTS module_archiver_jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT NOT NULL,
    drive_path  TEXT NOT NULL,
    drive_label TEXT NOT NULL DEFAULT '',
    project_id  TEXT NOT NULL,
    folder_name TEXT NOT NULL,
    target_path TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running',
    pct         INTEGER NOT NULL DEFAULT 0,
    files_done  INTEGER NOT NULL DEFAULT 0,
    files_total INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    started_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_archiver_jobs_user ON module_archiver_jobs("user");
