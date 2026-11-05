-- Vibe (vibe/PLAN-V1.md Baustein 6): Fortschritt der Einrichtung und Fehlergrund je Projekt.
ALTER TABLE module_vibe_projects ADD COLUMN progress    TEXT NOT NULL DEFAULT '';
ALTER TABLE module_vibe_projects ADD COLUMN error_code  TEXT NOT NULL DEFAULT '';
ALTER TABLE module_vibe_projects ADD COLUMN error_step  TEXT NOT NULL DEFAULT '';
