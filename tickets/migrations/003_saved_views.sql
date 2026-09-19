CREATE TABLE IF NOT EXISTS module_ticket_saved_views (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    team_id TEXT REFERENCES module_ticket_teams(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    filters_json TEXT NOT NULL DEFAULT '{}',
    sort TEXT NOT NULL DEFAULT 'updated_at',
    direction TEXT NOT NULL DEFAULT 'desc' CHECK (direction IN ('asc', 'desc')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_module_ticket_saved_views_owner
    ON module_ticket_saved_views (owner_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_module_ticket_saved_views_team
    ON module_ticket_saved_views (team_id, updated_at);
