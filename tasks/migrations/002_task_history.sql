-- Verlauf der Task-Beschreibungen (Task df2f2eb2, SPEC-HISTORY.md).
-- Vor jeder Änderung von Titel/Beschreibung wird die alte Fassung hier gesichert.
CREATE TABLE IF NOT EXISTS module_tasks_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES module_tasks(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('update', 'restored'))
);

CREATE INDEX IF NOT EXISTS idx_module_tasks_history_task ON module_tasks_history (task_id, changed_at);
