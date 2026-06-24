-- Cryptoboard — Cache für historische Tageskurse (EUR). Additiv, IF NOT EXISTS.
-- Historische Kurse ändern sich nie → einmal von CoinGecko holen, dauerhaft
-- cachen. GLOBAL (nicht user-scoped): Kurse sind öffentlich, für alle gleich.
CREATE TABLE IF NOT EXISTS module_cryptoboard_price_history (
    coin_id  TEXT NOT NULL,
    day      TEXT NOT NULL,          -- ISO-Datum YYYY-MM-DD
    price    REAL NOT NULL,          -- Tageskurs in EUR
    PRIMARY KEY (coin_id, day)
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_pricehist_coin
    ON module_cryptoboard_price_history(coin_id);
