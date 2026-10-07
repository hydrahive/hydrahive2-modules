-- Ghostwriter-Läufe im Hintergrund (Spec ghostwriter.md §9.2). Ein Lauf = eine Zeile.
-- Bücher liegen als Dateien im Projektordner; hier nur der Lauf-Zustand.
CREATE TABLE IF NOT EXISTS module_storyteller_runs (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    project_id TEXT NOT NULL,
    book_id TEXT NOT NULL,
    scope TEXT NOT NULL,                        -- chapter | from | book
    model TEXT NOT NULL DEFAULT '',             -- leer = HydraHive-Standard
    options_json TEXT NOT NULL DEFAULT '{}',    -- skip_filled, length_words, limit_tokens
    progress_json TEXT NOT NULL DEFAULT '[]',   -- [{scene_id, state, words?}]
    status TEXT NOT NULL DEFAULT 'queued',      -- queued | running | done | cancelled | limit | error
    current_scene TEXT,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_micros INTEGER,                        -- NULL = Tarif unbekannt
    cost_partial INTEGER NOT NULL DEFAULT 0,    -- 1 = für einen Teil war kein Tarif bekannt
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_module_storyteller_runs_book
    ON module_storyteller_runs (project_id, book_id, created_at DESC);
