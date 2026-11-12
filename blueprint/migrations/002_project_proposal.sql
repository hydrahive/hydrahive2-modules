-- Projekt am Board und Vorschlag des Agenten (Etappe 3a, scratchpad/SPEC-IDEEN.md).
-- project_id: Projekt, zu dem das Board gehört, oder leer.
-- proposal_*: höchstens ein offener Vorschlag des Agenten neben der Fassung des Nutzers (graph_json).
-- revision: zählt jede Änderung an graph_json. Eine offene Zeichenfläche nennt beim Speichern den Stand,
--   den sie kennt, und überschreibt so nichts, was inzwischen der Agent oder ein anderes Fenster gezeichnet hat.
-- Bestehende Boards behalten ihre Daten, die neuen Felder sind dort leer, der Zähler steht auf 0.
ALTER TABLE module_blueprint_boards ADD COLUMN project_id TEXT;
ALTER TABLE module_blueprint_boards ADD COLUMN proposal_json TEXT;
ALTER TABLE module_blueprint_boards ADD COLUMN proposal_note TEXT;
ALTER TABLE module_blueprint_boards ADD COLUMN proposal_at TEXT;
ALTER TABLE module_blueprint_boards ADD COLUMN revision INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_blueprint_boards_project
    ON module_blueprint_boards("user", project_id);
