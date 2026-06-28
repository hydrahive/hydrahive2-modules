-- Home Assistant — gepinnte Entities pro User fürs Dashboard. Additiv,
-- IF NOT EXISTS (No-op auf bestehenden DBs). Keine Geheimnisse hier — URL und
-- Token leben in den System-Settings (overrides.json). Daten bleiben bei
-- Deinstallation erhalten.
CREATE TABLE IF NOT EXISTS module_homeassistant_favorites (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"     TEXT    NOT NULL,
    entity_id  TEXT    NOT NULL,            -- z.B. light.wohnzimmer
    sort       INTEGER NOT NULL DEFAULT 0,  -- Reihenfolge im Dashboard
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_homeassistant_fav_user_entity
    ON module_homeassistant_favorites("user", entity_id);
CREATE INDEX IF NOT EXISTS idx_homeassistant_fav_user
    ON module_homeassistant_favorites("user");
