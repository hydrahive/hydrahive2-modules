-- Cryptoboard — Watchlist pro User. Additiv, IF NOT EXISTS (No-op auf
-- bestehenden DBs). Daten bleiben bei Deinstallation erhalten.
CREATE TABLE IF NOT EXISTS module_cryptoboard_watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    "user" TEXT NOT NULL,
    coin_id TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE("user", coin_id)
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_watchlist_user
    ON module_cryptoboard_watchlist("user");
