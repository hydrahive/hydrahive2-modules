-- TV-Werkstatt E2 (PLAN-E2.md): Aussehen je Fernseher, Apps des Fernsehers (zwischengespeichert), Hintergründe.
CREATE TABLE IF NOT EXISTS module_tvwerkstatt_looks (
    device_id   TEXT PRIMARY KEY REFERENCES module_tvwerkstatt_devices(device_id) ON DELETE CASCADE,
    look        TEXT NOT NULL,                       -- geprüftes JSON (backend/look.py)
    pushed_at   TEXT NOT NULL DEFAULT '',            -- zuletzt auf den Fernseher geschoben
    pushed_hash TEXT NOT NULL DEFAULT '',            -- sha256 der geschobenen config.json + Bilder
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS module_tvwerkstatt_apps (
    device_id   TEXT NOT NULL REFERENCES module_tvwerkstatt_devices(device_id) ON DELETE CASCADE,
    package     TEXT NOT NULL,
    label       TEXT NOT NULL DEFAULT '',
    version     TEXT NOT NULL DEFAULT '',            -- versionCode: neues Bild nur bei neuer Version
    has_banner  INTEGER NOT NULL DEFAULT 0,          -- 1 = Banner (16:9), 0 = nur Symbol
    color       TEXT NOT NULL DEFAULT '',            -- Grundfarbe des Bildes für Platzhalter
    read_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (device_id, package)
);

CREATE TABLE IF NOT EXISTS module_tvwerkstatt_wallpapers (
    wallpaper_id TEXT PRIMARY KEY,
    device_id    TEXT NOT NULL REFERENCES module_tvwerkstatt_devices(device_id) ON DELETE CASCADE,
    mood         TEXT NOT NULL,                      -- morning | evening | night
    file_name    TEXT NOT NULL,                      -- nur [a-z0-9-].jpg, vom Server vergeben
    title        TEXT NOT NULL DEFAULT '',
    sha256       TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS module_tvwerkstatt_wallpapers_dev ON module_tvwerkstatt_wallpapers (device_id, mood);
