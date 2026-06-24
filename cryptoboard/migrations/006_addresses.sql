-- Cryptoboard — On-Chain-Wallet-Adressen pro User. Additiv, IF NOT EXISTS.
-- Nur Adressen (öffentlich), NIEMALS Private Keys. Mehrere Adressen pro Chain
-- möglich. Bestände werden live von den Block-Explorern geholt, nicht gespeichert.
CREATE TABLE IF NOT EXISTS module_cryptoboard_addresses (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"    TEXT NOT NULL,
    chain     TEXT NOT NULL,           -- base | tron | bitcoin
    address   TEXT NOT NULL,
    label     TEXT NOT NULL DEFAULT '',
    added_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE("user", chain, address)
);
CREATE INDEX IF NOT EXISTS idx_cryptoboard_addr_user
    ON module_cryptoboard_addresses("user");
