-- TV-Werkstatt Apps: zuletzt gelesene selbst installierte Apps je Fernseher (nur lesend erhoben).
CREATE TABLE IF NOT EXISTS module_tvwerkstatt_store_reads (
    device_id  TEXT PRIMARY KEY REFERENCES module_tvwerkstatt_devices(device_id) ON DELETE CASCADE,
    apps       TEXT NOT NULL,                        -- JSON [{package, version_code, version_name, installer, enabled}]
    read_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
