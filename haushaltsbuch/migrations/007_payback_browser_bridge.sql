PRAGMA foreign_keys = ON;

ALTER TABLE module_haushaltsbuch_loyalty_activities
  ADD COLUMN purchase_amount_minor INTEGER
  CHECK(purchase_amount_minor IS NULL OR purchase_amount_minor >= 0);
ALTER TABLE module_haushaltsbuch_loyalty_activities
  ADD COLUMN purchase_currency TEXT
  CHECK(purchase_currency IS NULL OR (length(purchase_currency) = 3 AND purchase_currency = upper(purchase_currency)));

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_payback_bridge_flows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flow_id TEXT NOT NULL UNIQUE CHECK(length(flow_id) BETWEEN 32 AND 36),
  code_hmac TEXT NOT NULL UNIQUE CHECK(length(code_hmac) = 64),
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  member_id INTEGER NOT NULL,
  alias TEXT CHECK(alias IS NULL OR length(alias) BETWEEN 1 AND 120),
  visibility TEXT NOT NULL CHECK(visibility IN ('owner','household')),
  expires_at TEXT NOT NULL,
  consumed_at TEXT,
  connection_id INTEGER,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  CHECK(consumed_at IS NULL OR connection_id IS NOT NULL),
  FOREIGN KEY(member_id, household_id)
    REFERENCES module_haushaltsbuch_members(id, household_id) ON DELETE CASCADE,
  FOREIGN KEY(connection_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_connections(id, household_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hh_payback_bridge_flow_owner
  ON module_haushaltsbuch_payback_bridge_flows(member_id, flow_id);
CREATE INDEX IF NOT EXISTS idx_hh_payback_bridge_flow_expiry
  ON module_haushaltsbuch_payback_bridge_flows(expires_at, consumed_at);
