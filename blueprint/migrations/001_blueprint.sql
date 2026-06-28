-- Blueprint — visueller Node-Editor: Boards pro User. Additiv, IF NOT EXISTS
-- (No-op auf bestehenden DBs). graph_json hält den xyflow-Graphen
-- ({"nodes":[...],"edges":[...]}). Daten bleiben bei Deinstallation erhalten.
CREATE TABLE IF NOT EXISTS module_blueprint_boards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT    NOT NULL,
    name        TEXT    NOT NULL DEFAULT 'Neues Board',
    graph_json  TEXT    NOT NULL DEFAULT '{"nodes":[],"edges":[]}',
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_blueprint_boards_user
    ON module_blueprint_boards("user");
