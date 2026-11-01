-- Modul Netzwerk, Etappe 1a (network/PLAN-E1.md). Nur lesende Daten über das eigene Netz.
-- Zugänge: nur der NAME des Safe-Eintrags, nie das Geheimnis.
CREATE TABLE IF NOT EXISTS module_network_config (
    config_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    udm_url TEXT,
    udm_credential TEXT,
    udm_pin TEXT,
    fritz_host TEXT,
    fritz_credential TEXT,
    plan_down_mbit REAL,
    plan_up_mbit REAL,
    plan_price_eur REAL,
    last_full_sync INTEGER,
    last_status TEXT,
    last_status_at INTEGER,
    last_error TEXT,
    updated_at TEXT NOT NULL
);

-- Eigene Messung, eine Zeile je Minute. Weg: cable | mobile | none | unknown.
CREATE TABLE IF NOT EXISTS module_network_samples (
    ts INTEGER PRIMARY KEY,
    lan_loss REAL,
    lan_rtt REAL,
    fritz_loss REAL,
    fritz_rtt REAL,
    inet_loss REAL,
    inet_rtt_min REAL,
    inet_rtt_avg REAL,
    inet_rtt_max REAL,
    inet_jitter REAL,
    fritz_link TEXT,
    fritz_conn TEXT,
    fritz_access TEXT,
    path TEXT NOT NULL DEFAULT 'unknown' CHECK(path IN ('cable','mobile','none','unknown'))
);

-- Ereignisse aus Geräten (Dream Machine, später FRITZ!Box). event_id aus der Quelle → keine Dubletten.
CREATE TABLE IF NOT EXISTS module_network_events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    ts INTEGER NOT NULL,
    kind TEXT NOT NULL,
    wan TEXT,
    duration_s INTEGER,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_network_events_ts ON module_network_events(ts);

CREATE TABLE IF NOT EXISTS module_network_speedtests (
    source TEXT NOT NULL,
    ts INTEGER NOT NULL,
    down_mbit REAL,
    up_mbit REAL,
    ping_ms REAL,
    server TEXT,
    PRIMARY KEY (source, ts)
);

-- Verlauf aus der Dream Machine (sie löscht 5 min nach 24 h, Stunde nach 7 Tagen) – hier dauerhaft.
CREATE TABLE IF NOT EXISTS module_network_udm_series (
    scale TEXT NOT NULL CHECK(scale IN ('5min','hour','day')),
    ts INTEGER NOT NULL,
    latency_avg REAL,
    latency_min REAL,
    latency_max REAL,
    rx_bytes REAL,
    tx_bytes REAL,
    PRIMARY KEY (scale, ts)
);
