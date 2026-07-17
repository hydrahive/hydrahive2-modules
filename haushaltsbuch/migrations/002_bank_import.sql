PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_import_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
  delimiter TEXT NOT NULL CHECK(delimiter IN (';', ',', char(9))),
  encoding TEXT NOT NULL CHECK(encoding IN ('utf-8','utf-8-sig','cp1252','iso-8859-1')),
  decimal_separator TEXT NOT NULL CHECK(decimal_separator IN ('.', ',')),
  date_format TEXT NOT NULL CHECK(length(date_format) BETWEEN 1 AND 40),
  mapping_json TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(household_id, name), UNIQUE(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_import_batches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  account_id INTEGER NOT NULL,
  profile_id INTEGER,
  display_filename TEXT NOT NULL CHECK(length(display_filename) BETWEEN 1 AND 255),
  source_format TEXT NOT NULL CHECK(source_format IN ('camt','mt940','csv')),
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

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_import_rows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  batch_id INTEGER NOT NULL,
  source_line INTEGER NOT NULL CHECK(source_line > 0),
  booking_date TEXT,
  value_date TEXT,
  amount_minor INTEGER,
  currency TEXT CHECK(currency IS NULL OR length(currency) = 3),
  counterparty TEXT,
  purpose TEXT,
  counterparty_identifier TEXT,
  bank_reference TEXT,
  category_hint TEXT,
  warnings_json TEXT NOT NULL DEFAULT '[]',
  errors_json TEXT NOT NULL DEFAULT '[]',
  fingerprint TEXT NOT NULL CHECK(length(fingerprint) = 64),
  fingerprint_strength TEXT NOT NULL CHECK(fingerprint_strength IN ('strong','weak')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected','duplicate','error','imported','reversed')),
  category_id INTEGER,
  transaction_id INTEGER,
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(batch_id, source_line), UNIQUE(id, household_id),
  FOREIGN KEY(batch_id, household_id) REFERENCES module_haushaltsbuch_import_batches(id, household_id) ON DELETE CASCADE,
  FOREIGN KEY(category_id, household_id) REFERENCES module_haushaltsbuch_categories(id, household_id),
  FOREIGN KEY(transaction_id, household_id) REFERENCES module_haushaltsbuch_transactions(id, household_id)
);

CREATE INDEX IF NOT EXISTS idx_hh_import_profiles_household ON module_haushaltsbuch_import_profiles(household_id);
CREATE INDEX IF NOT EXISTS idx_hh_import_batches_household ON module_haushaltsbuch_import_batches(household_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_hh_import_rows_batch ON module_haushaltsbuch_import_rows(batch_id, id);
CREATE INDEX IF NOT EXISTS idx_hh_import_rows_fingerprint ON module_haushaltsbuch_import_rows(household_id, fingerprint, status);
