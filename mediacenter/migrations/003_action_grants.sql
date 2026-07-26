CREATE TABLE module_mediacenter_action_grants (
    grant_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    session_id TEXT NOT NULL,
    result_id TEXT NOT NULL,
    media_type TEXT NOT NULL CHECK(media_type IN ('movie','tv','book','audiobook','audioplay','music')),
    operation TEXT NOT NULL CHECK(operation = 'enqueue'),
    turn_fingerprint TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(owner, session_id, operation, turn_fingerprint)
);
CREATE INDEX idx_mediacenter_grants_binding
    ON module_mediacenter_action_grants(owner, session_id, result_id, expires_at);
