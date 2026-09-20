CREATE TABLE IF NOT EXISTS module_ticket_github_connections (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    owner TEXT NOT NULL,
    repository TEXT NOT NULL,
    project_number INTEGER,
    project_node_id TEXT,
    credential_name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    sync_mode TEXT NOT NULL DEFAULT 'read_only'
        CHECK (sync_mode IN ('read_only', 'push', 'bidirectional')),
    last_error TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (project_id, owner, repository, project_number)
);

CREATE TABLE IF NOT EXISTS module_ticket_github_links (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL UNIQUE REFERENCES module_tickets(id) ON DELETE CASCADE,
    connection_id TEXT NOT NULL REFERENCES module_ticket_github_connections(id) ON DELETE CASCADE,
    owner TEXT NOT NULL,
    repository TEXT NOT NULL,
    issue_number INTEGER NOT NULL CHECK (issue_number > 0),
    issue_node_id TEXT,
    project_node_id TEXT,
    project_item_id TEXT,
    issue_url TEXT NOT NULL,
    sync_state TEXT NOT NULL DEFAULT 'linked'
        CHECK (sync_state IN ('linked', 'stale', 'error')),
    last_synced_at TEXT,
    last_error TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (owner, repository, issue_number)
);

CREATE INDEX IF NOT EXISTS idx_ticket_github_connections_project
    ON module_ticket_github_connections (project_id, enabled);
CREATE INDEX IF NOT EXISTS idx_ticket_github_links_connection
    ON module_ticket_github_links (connection_id, sync_state);
