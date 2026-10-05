-- Mining: Clore-Probelauf (nur rechnen, nichts mieten). 14 Tage Aufbewahrung.
CREATE TABLE IF NOT EXISTS module_mining_clore_runs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,          -- ISO-UTC
    ok        INTEGER NOT NULL,       -- 0 = Abruf/Kurse fehlten, nichts gerechnet
    free      INTEGER NOT NULL,
    rated     INTEGER NOT NULL,
    hits      INTEGER NOT NULL,
    best_roi  REAL,
    error     TEXT
);
CREATE INDEX IF NOT EXISTS idx_module_mining_clore_runs_ts ON module_mining_clore_runs(ts);

CREATE TABLE IF NOT EXISTS module_mining_clore_hits (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  INTEGER NOT NULL,
    ts      TEXT NOT NULL,
    data    TEXT NOT NULL             -- JSON: server_id, gpu, count, coin, source, revenue, cost_*, roi_*, …
);
CREATE INDEX IF NOT EXISTS idx_module_mining_clore_hits_ts ON module_mining_clore_hits(ts);
