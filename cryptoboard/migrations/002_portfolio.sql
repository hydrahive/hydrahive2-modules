-- Cryptoboard — Portfolio-Transaktions-Ledger pro User. Additiv, IF NOT EXISTS
-- (No-op auf bestehenden DBs). Holdings & P&L werden aus den Transaktionen
-- berechnet (FIFO). Alle Geldwerte in EUR (feste Portfolio-Währung).
-- Daten bleiben bei Deinstallation erhalten.
CREATE TABLE IF NOT EXISTS module_cryptoboard_transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT    NOT NULL,
    coin_id     TEXT    NOT NULL,
    symbol      TEXT    NOT NULL DEFAULT '',
    name        TEXT    NOT NULL DEFAULT '',
    kind        TEXT    NOT NULL,            -- buy | sell | transfer_in | transfer_out
    quantity    REAL    NOT NULL,            -- immer > 0
    price       REAL    NOT NULL DEFAULT 0,  -- Stückpreis in EUR (transfer: 0 erlaubt)
    fee         REAL    NOT NULL DEFAULT 0,  -- Gebühr in EUR
    executed_at TEXT    NOT NULL,            -- ISO-Zeitpunkt (bestimmt FIFO-Reihenfolge)
    note        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_tx_user
    ON module_cryptoboard_transactions("user");
CREATE INDEX IF NOT EXISTS idx_cryptoboard_tx_user_coin
    ON module_cryptoboard_transactions("user", coin_id);
