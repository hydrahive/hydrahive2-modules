-- Cryptoboard — eigenständige Preis-/Portfolio-Alerts pro User. Additiv,
-- IF NOT EXISTS. Neben den bestehenden Butler-Flows: einfache Regeln, die der
-- Poller direkt prüft und bei Schwellen-Übertritt als In-App-Event festhält.
-- Alle Geldwerte in EUR.
CREATE TABLE IF NOT EXISTS module_cryptoboard_alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT    NOT NULL,
    kind        TEXT    NOT NULL,            -- price_above | price_below | pct_change_24h_above | pct_change_24h_below | portfolio_above | portfolio_below
    coin_id     TEXT    NOT NULL DEFAULT '', -- leer bei portfolio_*
    symbol      TEXT    NOT NULL DEFAULT '',
    threshold   REAL    NOT NULL,
    active      INTEGER NOT NULL DEFAULT 1,
    last_value  REAL,                        -- letzter beobachteter Wert (Crossing-Erkennung)
    last_fired  TEXT    NOT NULL DEFAULT '',
    note        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_alerts_user
    ON module_cryptoboard_alerts("user");

-- In-App-Benachrichtigungs-Historie: ein Eintrag pro Auslösung.
CREATE TABLE IF NOT EXISTS module_cryptoboard_alert_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT    NOT NULL,
    alert_id    INTEGER NOT NULL,
    kind        TEXT    NOT NULL,
    coin_id     TEXT    NOT NULL DEFAULT '',
    symbol      TEXT    NOT NULL DEFAULT '',
    threshold   REAL    NOT NULL,
    value       REAL    NOT NULL,            -- Wert beim Auslösen
    message     TEXT    NOT NULL DEFAULT '',
    seen        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_alert_events_user
    ON module_cryptoboard_alert_events("user", seen);
