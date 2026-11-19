-- Phase 2: PDF-Kontoauszug und PayPal-CSV als Importquellen. SQLite kann einen
-- CHECK nicht per ALTER ändern -> Tabelle neu anlegen und Daten übernehmen.
--
-- WICHTIG: foreign_keys muss für den Rebuild AUS sein. module_haushaltsbuch_import_rows
-- hat eine FOREIGN KEY(batch_id, household_id) REFERENCES ...import_batches(id, household_id)
-- OHNE ON DELETE CASCADE-Schutz vor DROP: Ist foreign_keys=ON aktiv, löscht SQLite beim
-- DROP TABLE module_haushaltsbuch_import_batches sonst(!) über die ON DELETE CASCADE-Klausel
-- der referenzierenden Fremdschlüssel sämtliche Zeilen in import_rows mit - geprüft, das
-- passiert tatsächlich. Deshalb hier zuerst ausschalten und am Ende wieder einschalten.
--
-- Wiederholbar: Ein Rest von einem abgebrochenen Lauf (_new) wird zuerst entfernt. Wichtig,
-- weil der Kern-Migrator eine Migration mit "already exists" als erledigt markieren würde
-- (modules/migrations.py) - dann bliebe der alte CHECK.
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS module_haushaltsbuch_import_batches_new;
CREATE TABLE module_haushaltsbuch_import_batches_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  account_id INTEGER NOT NULL,
  profile_id INTEGER,
  display_filename TEXT NOT NULL CHECK(length(display_filename) BETWEEN 1 AND 255),
  source_format TEXT NOT NULL CHECK(source_format IN ('camt','mt940','csv','pdf','paypal')),
  file_hash TEXT NOT NULL CHECK(length(file_hash) = 64),
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','imported','reversed')),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  completed_at TEXT,
  reversed_at TEXT,
  UNIQUE(household_id, file_hash), UNIQUE(id, household_id),
  FOREIGN KEY(account_id, household_id) REFERENCES module_haushaltsbuch_accounts(id, household_id),
  FOREIGN KEY(profile_id, household_id) REFERENCES module_haushaltsbuch_import_profiles(id, household_id)
);
INSERT INTO module_haushaltsbuch_import_batches_new(
  id, household_id, account_id, profile_id, display_filename, source_format,
  file_hash, status, revision, created_by, created_at, updated_at, completed_at, reversed_at
)
  SELECT
    id, household_id, account_id, profile_id, display_filename, source_format,
    file_hash, status, revision, created_by, created_at, updated_at, completed_at, reversed_at
  FROM module_haushaltsbuch_import_batches;
DROP TABLE module_haushaltsbuch_import_batches;
ALTER TABLE module_haushaltsbuch_import_batches_new RENAME TO module_haushaltsbuch_import_batches;

CREATE INDEX IF NOT EXISTS idx_hh_import_batches_household ON module_haushaltsbuch_import_batches(household_id, id DESC);

PRAGMA foreign_keys = ON;
