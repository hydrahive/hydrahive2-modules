-- TV-Werkstatt Entrümpeln Teil 2: was die Werkstatt abgeschaltet hat (für „Alles zurück“ und „Nach Update prüfen“)
-- und eine Sicherung des Stands vor der ersten Änderung je Fernseher.
CREATE TABLE IF NOT EXISTS module_tvwerkstatt_debloat_changes (
    device_id  TEXT NOT NULL REFERENCES module_tvwerkstatt_devices(device_id) ON DELETE CASCADE,
    package    TEXT NOT NULL,
    changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (device_id, package)
);

CREATE TABLE IF NOT EXISTS module_tvwerkstatt_debloat_backup (
    device_id  TEXT PRIMARY KEY REFERENCES module_tvwerkstatt_devices(device_id) ON DELETE CASCADE,
    packages   TEXT NOT NULL,                        -- JSON {paket: "on"|"off"} vor der ersten Änderung
    taken_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
