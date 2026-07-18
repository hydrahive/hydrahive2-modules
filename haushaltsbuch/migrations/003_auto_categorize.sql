-- Auto-Kategorisierung: Vorschläge auf Importzeilen (kein Auto-Buchen).
-- suggested_category_id  = vorgeschlagene Kategorie (FK, kann NULL sein)
-- suggestion_source      = Herkunft des Vorschlags: 'history' | 'llm'
-- suggestion_confidence  = 0.0–1.0, Vertrauen in den Vorschlag
ALTER TABLE module_haushaltsbuch_import_rows
  ADD COLUMN suggested_category_id INTEGER
  REFERENCES module_haushaltsbuch_categories(id);

ALTER TABLE module_haushaltsbuch_import_rows
  ADD COLUMN suggestion_source TEXT
  CHECK(suggestion_source IS NULL OR suggestion_source IN ('history','llm'));

ALTER TABLE module_haushaltsbuch_import_rows
  ADD COLUMN suggestion_confidence REAL
  CHECK(suggestion_confidence IS NULL OR (suggestion_confidence >= 0 AND suggestion_confidence <= 1));

CREATE INDEX IF NOT EXISTS idx_hh_import_rows_suggestion
  ON module_haushaltsbuch_import_rows(batch_id, suggested_category_id);
