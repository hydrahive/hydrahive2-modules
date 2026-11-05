-- Vibe (vibe/PLAN-V1.md Baustein 7): letzte Zeilen der Ausgabe eines gescheiterten Einrichtungsschritts.
ALTER TABLE module_vibe_projects ADD COLUMN error_detail TEXT NOT NULL DEFAULT '';
