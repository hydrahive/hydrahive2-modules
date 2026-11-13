-- TV-Werkstatt Baustein 4: was beim Bau herauskam (Version, Größe, Signatur) – zum Anzeigen und für den Abgleich vor dem
-- Installieren (Baustein 6).
ALTER TABLE module_tvwerkstatt_builds ADD COLUMN version TEXT NOT NULL DEFAULT '';
ALTER TABLE module_tvwerkstatt_builds ADD COLUMN size INTEGER NOT NULL DEFAULT 0;
ALTER TABLE module_tvwerkstatt_builds ADD COLUMN signer TEXT NOT NULL DEFAULT '';
