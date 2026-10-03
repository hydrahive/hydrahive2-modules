-- Mining-Modul E3–E5: Messungen, Laufzustand, Wechsel-Protokoll.

CREATE TABLE IF NOT EXISTS module_mining_benchmarks (
    rig_id       TEXT NOT NULL,
    coin         TEXT NOT NULL,
    miner        TEXT NOT NULL,
    algo         TEXT NOT NULL,
    hashrate     REAL,               -- H/s; NULL = Lauf fehlgeschlagen
    watts        REAL,
    error        TEXT,
    measured_at  TEXT NOT NULL,
    PRIMARY KEY (rig_id, coin, miner)
);

-- Aktuelle Zuteilung je Rig (vom Entscheider gesetzt, Rig folgt).
CREATE TABLE IF NOT EXISTS module_mining_assignments (
    rig_id      TEXT PRIMARY KEY,
    mode        TEXT NOT NULL,       -- mine | benchmark | stop
    coin        TEXT,
    miner       TEXT,
    algo        TEXT,
    reason      TEXT,
    since       TEXT NOT NULL,
    power_since TEXT                 -- E5: seit wann an/aus wegen Energie
);

CREATE TABLE IF NOT EXISTS module_mining_switch_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    rig_id     TEXT NOT NULL,
    from_coin  TEXT,
    to_coin    TEXT,
    reason     TEXT NOT NULL,
    at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_module_mining_switch_log_rig ON module_mining_switch_log(rig_id, at);
