-- TV-Werkstatt G1: HydraHive-App auf Fernsehern und Tablets. Kopplung per Einmal-Code, danach eigener Schlüssel je Gerät
-- (nur als SHA-256 gespeichert). Muster: Modul mining (pairing.py, rigs.py).
CREATE TABLE IF NOT EXISTS module_tvwerkstatt_app_pairing (
    code_hash   TEXT PRIMARY KEY,                     -- sha256 des Codes ohne Bindestriche
    name        TEXT NOT NULL,                        -- Anzeigename des künftigen App-Geräts (vom Admin)
    device_id   TEXT NOT NULL DEFAULT '',             -- optional: zu diesem Fernseher der Werkstatt
    expires_at  TEXT NOT NULL,
    used_at     TEXT,
    created_by  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS module_tvwerkstatt_app_devices (
    app_id      TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    device_id   TEXT NOT NULL DEFAULT '',             -- Fernseher der Werkstatt, falls zugeordnet (sonst z. B. Tablet)
    kind        TEXT NOT NULL DEFAULT '',             -- tv | tablet (von der App gemeldet)
    model       TEXT NOT NULL DEFAULT '',
    android     TEXT NOT NULL DEFAULT '',
    app_version TEXT NOT NULL DEFAULT '',
    token_hash  TEXT,                                 -- NULL = gesperrt
    status      TEXT NOT NULL DEFAULT 'active',       -- active | revoked
    remote_ip   TEXT NOT NULL DEFAULT '',
    state       TEXT NOT NULL DEFAULT '{}',           -- zuletzt gemeldeter Zustand (JSON, begrenzt)
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    last_seen   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_tvw_app_devices_token ON module_tvwerkstatt_app_devices(token_hash);

-- Was die App melden kann (Ereignisse) und was Hydra an sie schickt (Einblendungen) – kurz gehalten, alt wird gekappt.
CREATE TABLE IF NOT EXISTS module_tvwerkstatt_app_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id      TEXT NOT NULL REFERENCES module_tvwerkstatt_app_devices(app_id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    data        TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS module_tvwerkstatt_app_notices (
    notice_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id      TEXT NOT NULL REFERENCES module_tvwerkstatt_app_devices(app_id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    buttons     TEXT NOT NULL DEFAULT '[]',           -- JSON-Liste kurzer Texte
    answer      TEXT NOT NULL DEFAULT '',             -- gewählter Knopf (von der App)
    created_by  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    delivered_at TEXT NOT NULL DEFAULT '',
    answered_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_tvw_app_notices_app ON module_tvwerkstatt_app_notices(app_id, notice_id);
