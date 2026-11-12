-- Projekt am Board und Vorschlag des Agenten (Etappe 3a, scratchpad/SPEC-IDEEN.md).
-- project_id: Projekt, zu dem das Board gehört, oder leer.
-- proposal_*: höchstens ein offener Vorschlag des Agenten neben der Fassung des Nutzers (graph_json).
-- Bestehende Boards behalten ihre Daten, die neuen Felder sind dort leer.
ALTER TABLE module_blueprint_boards ADD COLUMN project_id TEXT;
ALTER TABLE module_blueprint_boards ADD COLUMN proposal_json TEXT;
ALTER TABLE module_blueprint_boards ADD COLUMN proposal_note TEXT;
ALTER TABLE module_blueprint_boards ADD COLUMN proposal_at TEXT;

CREATE INDEX IF NOT EXISTS idx_blueprint_boards_project
    ON module_blueprint_boards("user", project_id);
