CREATE TABLE IF NOT EXISTS module_ticket_teams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS module_ticket_team_members (
    team_id TEXT NOT NULL REFERENCES module_ticket_teams(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'lead')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (team_id, user_id)
);

CREATE TABLE IF NOT EXISTS module_tickets (
    number INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'triaged', 'in_progress', 'waiting', 'resolved', 'closed', 'cancelled')),
    priority TEXT NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    category TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    created_by TEXT NOT NULL,
    assigned_to TEXT,
    team_id TEXT REFERENCES module_ticket_teams(id) ON DELETE SET NULL,
    project_id TEXT,
    task_id TEXT,
    session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    resolved_at TEXT,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS module_ticket_comments (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES module_tickets(id) ON DELETE CASCADE,
    author_id TEXT NOT NULL,
    author_kind TEXT NOT NULL CHECK (author_kind IN ('user', 'agent')),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS module_ticket_events (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES module_tickets(id) ON DELETE CASCADE,
    actor_id TEXT NOT NULL,
    actor_kind TEXT NOT NULL CHECK (actor_kind IN ('user', 'agent', 'system')),
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS module_ticket_notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL REFERENCES module_tickets(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    read_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS module_ticket_attachments (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES module_tickets(id) ON DELETE CASCADE,
    comment_id TEXT REFERENCES module_ticket_comments(id) ON DELETE SET NULL,
    original_name TEXT NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    media_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    sha256 TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_module_tickets_status
    ON module_tickets (status, priority, updated_at);
CREATE INDEX IF NOT EXISTS idx_module_tickets_assigned_to
    ON module_tickets (assigned_to, status);
CREATE INDEX IF NOT EXISTS idx_module_tickets_team
    ON module_tickets (team_id, status);
CREATE INDEX IF NOT EXISTS idx_module_tickets_project
    ON module_tickets (project_id);
CREATE INDEX IF NOT EXISTS idx_module_ticket_comments_ticket
    ON module_ticket_comments (ticket_id, created_at);
CREATE INDEX IF NOT EXISTS idx_module_ticket_events_ticket
    ON module_ticket_events (ticket_id, created_at);
CREATE INDEX IF NOT EXISTS idx_module_ticket_notifications_user
    ON module_ticket_notifications (user_id, read_at, created_at);
