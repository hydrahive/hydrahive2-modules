-- Etappe B (VERTRAG-B.md): neue Importquelle 'crypto_ledger' (Swaps/
-- Kartenzahlungen/Abgaenge aus dem Cryptoboard-Ledger, Read-Port v3
-- ledger_moves). SQLite kann einen CHECK nicht per ALTER aendern -> Tabelle
-- neu anlegen und Daten uebernehmen (gleiches Muster wie 009/010).
--
-- WICHTIG (Lehre aus 009/010): foreign_keys muss fuer den Rebuild AUS sein.
-- module_haushaltsbuch_import_rows hat eine
-- FOREIGN KEY(batch_id, household_id) REFERENCES ...import_batches(id, household_id)
-- OHNE ON DELETE CASCADE-Schutz vor DROP: Ist foreign_keys=ON aktiv, loescht
-- SQLite beim DROP TABLE module_haushaltsbuch_import_batches sonst ueber die
-- referenzierenden Fremdschluessel saemtliche Zeilen in import_rows mit.
-- Deshalb hier zuerst ausschalten und am Ende wieder einschalten.
--
-- Wiederholbar: Ein Rest von einem abgebrochenen Lauf (_new) wird zuerst
-- entfernt. Wichtig, weil der Kern-Migrator eine Migration mit "already
-- exists" als erledigt markieren wuerde (modules/migrations.py) - dann
-- bliebe der alte CHECK.
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS module_haushaltsbuch_import_batches_new;
CREATE TABLE module_haushaltsbuch_import_batches_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  account_id INTEGER NOT NULL,
  profile_id INTEGER,
  display_filename TEXT NOT NULL CHECK(length(display_filename) BETWEEN 1 AND 255),
  source_format TEXT NOT NULL CHECK(source_format IN ('camt','mt940','csv','pdf','paypal','crypto_trades','crypto_ledger')),
  file_hash TEXT NOT NULL CHECK(length(file_hash) = 64),
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','imported','reversed')),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  completed_at TEXT,
  reversed_at TEXT,
  detected_bank_id TEXT,
  detected_bank_label TEXT,
  detected_encoding TEXT,
  UNIQUE(household_id, file_hash), UNIQUE(id, household_id),
  FOREIGN KEY(account_id, household_id) REFERENCES module_haushaltsbuch_accounts(id, household_id),
  FOREIGN KEY(profile_id, household_id) REFERENCES module_haushaltsbuch_import_profiles(id, household_id)
);
INSERT INTO module_haushaltsbuch_import_batches_new(
  id, household_id, account_id, profile_id, display_filename, source_format,
  file_hash, status, revision, created_by, created_at, updated_at, completed_at, reversed_at,
  detected_bank_id, detected_bank_label, detected_encoding
)
  SELECT
    id, household_id, account_id, profile_id, display_filename, source_format,
    file_hash, status, revision, created_by, created_at, updated_at, completed_at, reversed_at,
    detected_bank_id, detected_bank_label, detected_encoding
  FROM module_haushaltsbuch_import_batches;
DROP TABLE module_haushaltsbuch_import_batches;
ALTER TABLE module_haushaltsbuch_import_batches_new RENAME TO module_haushaltsbuch_import_batches;

CREATE INDEX IF NOT EXISTS idx_hh_import_batches_household ON module_haushaltsbuch_import_batches(household_id, id DESC);

PRAGMA foreign_keys = ON;

-- import_rows: ob eine Zeile Teil der Vorschau-"Gruppe" Kartenzahlung/Abgang/
-- Swap/unklar ist, steht schon in bank_reference (Cryptoboard-id) +
-- counter_account_id (Swap) bzw. category_id (Kartenzahlung/Abgang, siehe
-- "Ohne Kategorie"-Loesung in crypto_ledger_import.py); keine neue Spalte
-- noetig fuer die Gruppierung selbst. Abgaenge werden ueber den bestehenden
-- Row-Status 'rejected' (siehe import_models.ImportRowUpdate, bislang nur
-- vom Frontend gesetzt) standardmaessig exkludiert - Till kann sie wie jede
-- andere Zeile nachtraeglich auf 'pending'/'accepted' patchen.

-- Kategorien: "internal"-Flag fuer System-Kategorien wie "Ohne Kategorie"
-- (VERTRAG-B.md, "Kategorie bei Kartenzahlungen"). Anders als bei accounts
-- (internal=1 wird aus der normalen Liste gefiltert, assets.list_accounts)
-- bleibt eine interne Kategorie in list_categories SICHTBAR und waehlbar -
-- Till soll sie sehen, filtern (C3 "ohne Kategorie") und umkategorisieren
-- koennen. "internal" markiert hier nur "vom System angelegt, nicht
-- Till-erstellt", keine Sonderbehandlung in assets.py noetig.
ALTER TABLE module_haushaltsbuch_categories ADD COLUMN internal INTEGER NOT NULL DEFAULT 0 CHECK(internal IN (0,1));

-- import_rows: Zeilen-eigenes Hauptkonto fuer crypto_ledger-Zeilen. Anders
-- als beim Trade-Import (ein fiat_account_id fuer den GANZEN Batch, siehe
-- crypto_trade_import.py) mischt ein Ledger-Import mehrere Kontopaare in
-- EINEM Batch (Swap Tron->Base, Swap Tron->Ethereum, Kartenzahlung von Base
-- ODER Ethereum - je nachdem, welche Adresse am Zug war). row_account_id
-- ueberschreibt bei Nicht-NULL das Batch-Konto (import_batches.account_id)
-- fuer GENAU diese Zeile (import_completion.py); bleibt sie NULL, gilt wie
-- bisher das Batch-Konto (Trade-Import, Datei-Importe unveraendert).
ALTER TABLE module_haushaltsbuch_import_rows
  ADD COLUMN row_account_id INTEGER
  REFERENCES module_haushaltsbuch_accounts(id);

CREATE INDEX IF NOT EXISTS idx_hh_import_rows_row_account
  ON module_haushaltsbuch_import_rows(row_account_id);
