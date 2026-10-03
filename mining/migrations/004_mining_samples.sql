-- Mining: Verlauf für das Diagramm (höchstens 1 Probe pro Rig und Minute, 7 Tage).
CREATE TABLE IF NOT EXISTS module_mining_samples (
    rig_id  TEXT NOT NULL,
    ts      TEXT NOT NULL,          -- ISO-UTC, auf die Minute gerundet
    data    TEXT NOT NULL,          -- JSON: mode, coin, miner, usd_day, pct, cards[]
    PRIMARY KEY (rig_id, ts)
);

CREATE INDEX IF NOT EXISTS idx_module_mining_samples_ts ON module_mining_samples(ts);
