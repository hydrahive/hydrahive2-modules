-- Frühere Fassungen eines Boards (Etappe 3a). Vor dem Übernehmen eines Vorschlags und vor dem
-- Wiederherstellen wird die bisherige Fassung hier gesichert. Je Board bleiben die letzten 20.
CREATE TABLE IF NOT EXISTS module_blueprint_versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id    INTEGER NOT NULL REFERENCES module_blueprint_boards(id) ON DELETE CASCADE,
    graph_json  TEXT    NOT NULL,
    node_count  INTEGER NOT NULL DEFAULT 0,
    source      TEXT    NOT NULL CHECK (source IN ('proposal', 'restore')),
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_blueprint_versions_board
    ON module_blueprint_versions(board_id, id);
