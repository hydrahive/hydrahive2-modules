-- Vibe (vibe/PLAN-V1.md): Projekte und Versionen. Ein Vibe-Projekt = ein Kern-Projekt + ein Container.
CREATE TABLE IF NOT EXISTS module_vibe_projects (
    project_id    TEXT    PRIMARY KEY,
    agent_id      TEXT    NOT NULL,
    container     TEXT    NOT NULL UNIQUE,
    name          TEXT    NOT NULL,
    owner         TEXT    NOT NULL,
    state         TEXT    NOT NULL DEFAULT 'new',
    heal_enabled  INTEGER NOT NULL DEFAULT 1,
    last_used_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS module_vibe_versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL REFERENCES module_vibe_projects(project_id) ON DELETE CASCADE,
    commit_id   TEXT NOT NULL,
    summary     TEXT NOT NULL DEFAULT '',
    kind        TEXT NOT NULL DEFAULT 'turn',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (project_id, commit_id)
);
CREATE INDEX IF NOT EXISTS module_vibe_versions_project ON module_vibe_versions (project_id, id);
