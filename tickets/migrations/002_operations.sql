ALTER TABLE module_tickets ADD COLUMN response_due_at TEXT;
ALTER TABLE module_tickets ADD COLUMN resolution_due_at TEXT;
ALTER TABLE module_tickets ADD COLUMN due_at TEXT;
ALTER TABLE module_tickets ADD COLUMN manual_due_at TEXT;
ALTER TABLE module_tickets ADD COLUMN due_at_source TEXT NOT NULL DEFAULT 'none'
    CHECK (due_at_source IN ('sla', 'manual', 'none'));
ALTER TABLE module_tickets ADD COLUMN first_response_at TEXT;
ALTER TABLE module_tickets ADD COLUMN sla_profile_id TEXT;

CREATE TABLE IF NOT EXISTS module_ticket_sla_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    urgent_response_hours INTEGER NOT NULL CHECK (urgent_response_hours > 0),
    urgent_resolution_hours INTEGER NOT NULL CHECK (urgent_resolution_hours > 0),
    high_response_hours INTEGER NOT NULL CHECK (high_response_hours > 0),
    high_resolution_hours INTEGER NOT NULL CHECK (high_resolution_hours > 0),
    normal_response_hours INTEGER NOT NULL CHECK (normal_response_hours > 0),
    normal_resolution_hours INTEGER NOT NULL CHECK (normal_resolution_hours > 0),
    low_response_hours INTEGER NOT NULL CHECK (low_response_hours > 0),
    low_resolution_hours INTEGER NOT NULL CHECK (low_resolution_hours > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

INSERT OR IGNORE INTO module_ticket_sla_profiles (
    id, name, description,
    urgent_response_hours, urgent_resolution_hours,
    high_response_hours, high_resolution_hours,
    normal_response_hours, normal_resolution_hours,
    low_response_hours, low_resolution_hours
) VALUES (
    'default', 'Default', 'Initial editable ticket SLA profile',
    4, 24, 8, 72, 24, 120, 72, 240
);

CREATE INDEX IF NOT EXISTS idx_module_tickets_due_at
    ON module_tickets (due_at, status);
CREATE INDEX IF NOT EXISTS idx_module_tickets_sla_profile
    ON module_tickets (sla_profile_id);
