-- S2 (Spec §12.6): Zustand des Vorschaubilds. NULL = noch nie versucht, ok | fehlt (kein Chromium) | fehler.
ALTER TABLE module_diagrams ADD COLUMN preview_state TEXT;
