-- Minigames — Highscores pro User + globale Bestenliste. Additiv, IF NOT EXISTS.
-- Eine Zeile je gespieltes Spiel-Ende. Eigene Bestleistung = MAX(score) je
-- (user, game_id); Bestenliste = bester Score je User je game_id, absteigend.
CREATE TABLE IF NOT EXISTS module_minigames_scores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"     TEXT NOT NULL,
    game_id    TEXT NOT NULL,
    score      INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_minigames_scores_game
    ON module_minigames_scores(game_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_minigames_scores_user
    ON module_minigames_scores("user", game_id);
