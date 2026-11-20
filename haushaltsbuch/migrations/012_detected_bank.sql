-- Etappe Bank-CSV (hb-bank-csv-notes.md): Batch-Antwort bekommt optional
-- detected_bank/detected_encoding (nur Info fuer die UI, keine Logik-
-- Entscheidung haengt daran). additiv, wiederholbar (ADD COLUMN ohne
-- IF NOT EXISTS gibt es in SQLite nicht - deshalb ueber den Migrator
-- abgesichert wie alle anderen ALTER TABLE in diesem Modul).
ALTER TABLE module_haushaltsbuch_import_batches ADD COLUMN detected_bank_id TEXT;
ALTER TABLE module_haushaltsbuch_import_batches ADD COLUMN detected_bank_label TEXT;
ALTER TABLE module_haushaltsbuch_import_batches ADD COLUMN detected_encoding TEXT;
