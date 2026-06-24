-- Brettspiele — Partie-Ergebnisse pro User. Additiv, IF NOT EXISTS.
-- Eine Zeile je beendete Partie. result: 'win' | 'loss' | 'draw' (aus Sicht des
-- Users). mode: 'hotseat' | 'ai' | 'llm'. opponent: frei (z.B. Modell-ID bei llm).
CREATE TABLE IF NOT EXISTS module_boardgames_results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"     TEXT NOT NULL,
    game_id    TEXT NOT NULL,
    mode       TEXT NOT NULL,
    result     TEXT NOT NULL,
    opponent   TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_boardgames_results_game
    ON module_boardgames_results(game_id, result);
CREATE INDEX IF NOT EXISTS idx_boardgames_results_user
    ON module_boardgames_results("user", game_id);
