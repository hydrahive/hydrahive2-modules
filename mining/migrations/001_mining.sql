-- Mining-Modul E1: Kurs-/Pool-Cache und Einstellungen.
-- Rigs, Benchmarks, Zustände kommen mit E2/E3 in eigenen Migrationen.

CREATE TABLE IF NOT EXISTS module_mining_quotes (
    coin               TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    algo               TEXT NOT NULL,
    fee                REAL NOT NULL,
    fee_type           TEXT NOT NULL,
    profit_per_hs_day  REAL,
    price_usd          REAL,
    estimated          INTEGER NOT NULL DEFAULT 0,
    fetched_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS module_mining_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
