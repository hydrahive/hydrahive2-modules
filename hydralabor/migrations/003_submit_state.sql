-- Hydra-Labor L2: Eingaben und Ergebnis des laufenden/letzten Einreichens (für den Auftrag im Hintergrund).
ALTER TABLE module_hydralabor_state ADD COLUMN submit_in   TEXT NOT NULL DEFAULT '{}';
ALTER TABLE module_hydralabor_state ADD COLUMN submit_out  TEXT NOT NULL DEFAULT '{}';
