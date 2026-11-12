-- Ideen statt Freitext (SPEC-IDEEN.md, Task 954f2958).
-- task_id und board_id stehen schon hier, damit die Etappen 2 und 3 keine Tabellenänderung brauchen.
CREATE TABLE IF NOT EXISTS module_scratchpad_ideas (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    project_id TEXT,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    origin TEXT NOT NULL DEFAULT 'user',
    task_id TEXT,
    board_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_module_scratchpad_ideas_owner
    ON module_scratchpad_ideas (username, project_id, status);

CREATE TABLE IF NOT EXISTS module_scratchpad_idea_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id TEXT NOT NULL REFERENCES module_scratchpad_ideas(id) ON DELETE CASCADE,
    author TEXT NOT NULL,
    agent_name TEXT,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_module_scratchpad_idea_notes_idea
    ON module_scratchpad_idea_notes (idea_id, created_at);
