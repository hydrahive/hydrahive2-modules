PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_auth_flows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flow_id_hash TEXT NOT NULL UNIQUE CHECK(length(flow_id_hash) = 64),
  household_id INTEGER NOT NULL,
  member_id INTEGER NOT NULL,
  provider TEXT NOT NULL DEFAULT 'lidl_plus' CHECK(provider = 'lidl_plus'),
  scope TEXT NOT NULL CHECK(length(scope) BETWEEN 1 AND 500),
  expires_at TEXT NOT NULL,
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count BETWEEN 0 AND 3),
  processing_at TEXT,
  consumed_at TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(id, household_id),
  FOREIGN KEY(member_id, household_id)
    REFERENCES module_haushaltsbuch_members(id, household_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_receipts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  connection_id INTEGER NOT NULL,
  provider_receipt_id TEXT NOT NULL CHECK(length(provider_receipt_id) BETWEEN 1 AND 256),
  provider_fingerprint TEXT NOT NULL CHECK(length(provider_fingerprint) = 64),
  merchant_name TEXT NOT NULL CHECK(length(merchant_name) BETWEEN 1 AND 240),
  store_id TEXT CHECK(store_id IS NULL OR length(store_id) <= 256),
  store_name TEXT CHECK(store_name IS NULL OR length(store_name) <= 240),
  store_address TEXT CHECK(store_address IS NULL OR length(store_address) <= 1000),
  purchased_at TEXT,
  total_minor INTEGER,
  currency TEXT CHECK(currency IS NULL OR length(currency) = 3),
  total_discount_minor INTEGER CHECK(total_discount_minor IS NULL OR total_discount_minor >= 0),
  content_hash TEXT NOT NULL CHECK(length(content_hash) = 64),
  validation_status TEXT NOT NULL CHECK(validation_status IN ('valid','needs_review')),
  warnings_json TEXT NOT NULL DEFAULT '[]',
  first_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  last_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(connection_id, provider_receipt_id),
  UNIQUE(id, household_id),
  FOREIGN KEY(connection_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_connections(id, household_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_receipt_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  receipt_id INTEGER NOT NULL,
  sequence INTEGER NOT NULL CHECK(sequence >= 0),
  original_name TEXT NOT NULL CHECK(length(original_name) BETWEEN 1 AND 1000),
  gtin TEXT CHECK(gtin IS NULL OR length(gtin) BETWEEN 8 AND 14),
  quantity TEXT CHECK(quantity IS NULL OR length(quantity) <= 50),
  unit TEXT CHECK(unit IS NULL OR unit IN ('piece','kg')),
  unit_price_minor INTEGER,
  total_minor INTEGER,
  tax_group TEXT CHECK(tax_group IS NULL OR length(tax_group) <= 120),
  is_return INTEGER NOT NULL DEFAULT 0 CHECK(is_return IN (0,1)),
  UNIQUE(receipt_id, sequence),
  UNIQUE(id, household_id),
  FOREIGN KEY(receipt_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_receipts(id, household_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_receipt_adjustments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  receipt_id INTEGER NOT NULL,
  item_id INTEGER,
  kind TEXT NOT NULL CHECK(kind IN ('discount','coupon','deposit','rounding')),
  amount_minor INTEGER NOT NULL,
  description TEXT CHECK(description IS NULL OR length(description) <= 1000),
  FOREIGN KEY(receipt_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_receipts(id, household_id) ON DELETE CASCADE,
  FOREIGN KEY(item_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_receipt_items(id, household_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hh_loyalty_auth_flow_expiry
  ON module_haushaltsbuch_loyalty_auth_flows(expires_at, consumed_at);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_receipts_scope
  ON module_haushaltsbuch_loyalty_receipts(household_id, purchased_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_receipt_items
  ON module_haushaltsbuch_loyalty_receipt_items(receipt_id, sequence);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_receipt_adjustments
  ON module_haushaltsbuch_loyalty_receipt_adjustments(receipt_id, item_id);
