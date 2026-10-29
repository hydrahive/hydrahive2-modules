-- Fernseher – Einstellungen (eine Zeile, id = 1). Der Schlüssel liegt nur verschlüsselt hier (Präfix tv:v1:).
-- Additiv, IF NOT EXISTS. Daten bleiben bei Deinstallation erhalten.
CREATE TABLE IF NOT EXISTS module_fernseher_settings (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    name          TEXT    NOT NULL DEFAULT '',
    address       TEXT    NOT NULL,
    psk_sealed    TEXT    NOT NULL,
    volume_limit  INTEGER NOT NULL DEFAULT 60,
    updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_by    TEXT    NOT NULL DEFAULT ''
);
