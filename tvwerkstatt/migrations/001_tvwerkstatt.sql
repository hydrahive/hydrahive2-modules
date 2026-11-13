-- TV-Werkstatt (tvwerkstatt/SPEC.md, PLAN-E1.md): Geräte, Quellen, Bauten, Installiertes, Aufträge.
CREATE TABLE IF NOT EXISTS module_tvwerkstatt_devices (
    device_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    address     TEXT NOT NULL UNIQUE,            -- je Adresse eine Ausnahme in der Sperrliste
    adb_port    INTEGER NOT NULL DEFAULT 5555,
    kind        TEXT NOT NULL DEFAULT '',        -- android_tv | google_tv, gelesen, nicht angenommen
    model       TEXT NOT NULL DEFAULT '',
    android     TEXT NOT NULL DEFAULT '',
    sdk         INTEGER NOT NULL DEFAULT 0,
    build       TEXT NOT NULL DEFAULT '',
    stock_home  TEXT NOT NULL DEFAULT '',        -- Original-Startbildschirm, für den Rückweg
    live_tv     TEXT NOT NULL DEFAULT '',
    adb_state   TEXT NOT NULL DEFAULT 'unknown', -- unknown | open | closed | unauthorized
    checked_at  TEXT NOT NULL DEFAULT '',
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS module_tvwerkstatt_sources (
    source_id   TEXT PRIMARY KEY,
    repo        TEXT NOT NULL UNIQUE,
    commit_id   TEXT NOT NULL,
    license     TEXT NOT NULL DEFAULT '',
    checked_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS module_tvwerkstatt_builds (
    build_id    TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL REFERENCES module_tvwerkstatt_sources(source_id),
    part        TEXT NOT NULL,                   -- launcher oder Ordner eines Zusatzes
    commit_id   TEXT NOT NULL,
    sha256      TEXT NOT NULL DEFAULT '',
    package     TEXT NOT NULL DEFAULT '',
    state       TEXT NOT NULL DEFAULT 'new',     -- new | running | done | failed
    log_tail    TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS module_tvwerkstatt_installed (
    device_id     TEXT NOT NULL REFERENCES module_tvwerkstatt_devices(device_id) ON DELETE CASCADE,
    package       TEXT NOT NULL,
    build_id      TEXT NOT NULL,
    sha256        TEXT NOT NULL,
    installed_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (device_id, package)
);

CREATE TABLE IF NOT EXISTS module_tvwerkstatt_jobs (
    job_id        TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,                 -- setup | build | install | restore | probe
    target        TEXT NOT NULL DEFAULT '',
    state         TEXT NOT NULL DEFAULT 'new',   -- new | running | done | failed
    step          TEXT NOT NULL DEFAULT '',
    error_code    TEXT NOT NULL DEFAULT '',
    error_detail  TEXT NOT NULL DEFAULT '',
    started_by    TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS module_tvwerkstatt_jobs_state ON module_tvwerkstatt_jobs (state, created_at);
