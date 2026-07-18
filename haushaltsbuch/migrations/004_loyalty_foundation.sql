PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_connections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK(provider IN ('lidl_plus','payback')),
  owner_member_id INTEGER NOT NULL,
  credential_ref TEXT NOT NULL CHECK(length(credential_ref) BETWEEN 1 AND 500),
  account_fingerprint TEXT NOT NULL CHECK(length(account_fingerprint) BETWEEN 1 AND 256),
  masked_account TEXT NOT NULL CHECK(length(masked_account) BETWEEN 1 AND 120),
  alias TEXT CHECK(alias IS NULL OR length(alias) BETWEEN 1 AND 120),
  country_code TEXT NOT NULL DEFAULT 'DE' CHECK(length(country_code) = 2),
  language_code TEXT NOT NULL DEFAULT 'de' CHECK(length(language_code) BETWEEN 2 AND 16),
  visibility TEXT NOT NULL DEFAULT 'owner' CHECK(visibility IN ('owner','household')),
  status TEXT NOT NULL DEFAULT 'disconnected'
    CHECK(status IN ('disconnected','active','syncing','reauth_required','blocked','disabled','error')),
  capabilities_json TEXT NOT NULL DEFAULT '{}',
  feature_enabled INTEGER NOT NULL DEFAULT 0 CHECK(feature_enabled IN (0,1)),
  sync_enabled INTEGER NOT NULL DEFAULT 0 CHECK(sync_enabled IN (0,1)),
  sync_interval_hours INTEGER CHECK(sync_interval_hours IS NULL OR sync_interval_hours > 0),
  sync_cursor TEXT,
  last_sync_at TEXT,
  last_success_at TEXT,
  next_sync_at TEXT,
  last_error_code TEXT CHECK(last_error_code IS NULL OR length(last_error_code) BETWEEN 1 AND 120),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(household_id, provider, owner_member_id, account_fingerprint),
  UNIQUE(id, household_id),
  FOREIGN KEY(owner_member_id, household_id)
    REFERENCES module_haushaltsbuch_members(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_sync_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  connection_id INTEGER NOT NULL,
  trigger TEXT NOT NULL CHECK(trigger IN ('manual','scheduled')),
  started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  finished_at TEXT,
  status TEXT NOT NULL DEFAULT 'running'
    CHECK(status IN ('running','succeeded','partial','failed','cancelled')),
  cursor_before TEXT,
  cursor_after TEXT,
  fetched_count INTEGER NOT NULL DEFAULT 0 CHECK(fetched_count >= 0),
  created_count INTEGER NOT NULL DEFAULT 0 CHECK(created_count >= 0),
  updated_count INTEGER NOT NULL DEFAULT 0 CHECK(updated_count >= 0),
  skipped_count INTEGER NOT NULL DEFAULT 0 CHECK(skipped_count >= 0),
  error_code TEXT CHECK(error_code IS NULL OR length(error_code) BETWEEN 1 AND 120),
  next_allowed_attempt_at TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  CHECK(finished_at IS NULL OR finished_at >= started_at),
  CHECK((status = 'running' AND finished_at IS NULL) OR
        (status != 'running' AND finished_at IS NOT NULL)),
  UNIQUE(id, household_id),
  FOREIGN KEY(connection_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_connections(id, household_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_balances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  connection_id INTEGER NOT NULL,
  observed_at TEXT NOT NULL,
  available_points INTEGER NOT NULL CHECK(available_points >= 0),
  money_value_minor INTEGER CHECK(money_value_minor IS NULL OR money_value_minor >= 0),
  money_value_currency TEXT CHECK(money_value_currency IS NULL OR length(money_value_currency) = 3),
  valuation_version TEXT CHECK(valuation_version IS NULL OR length(valuation_version) BETWEEN 1 AND 120),
  fingerprint TEXT NOT NULL CHECK(length(fingerprint) BETWEEN 1 AND 256),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  CHECK((money_value_minor IS NULL AND money_value_currency IS NULL AND valuation_version IS NULL) OR
        (money_value_minor IS NOT NULL AND money_value_currency IS NOT NULL AND valuation_version IS NOT NULL)),
  UNIQUE(connection_id, fingerprint),
  UNIQUE(id, household_id),
  FOREIGN KEY(connection_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_connections(id, household_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_partners (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK(provider IN ('lidl_plus','payback')),
  provider_partner_id TEXT NOT NULL CHECK(length(provider_partner_id) BETWEEN 1 AND 256),
  name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 240),
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  first_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  last_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  CHECK(last_seen_at >= first_seen_at),
  UNIQUE(household_id, provider, provider_partner_id),
  UNIQUE(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_activities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  connection_id INTEGER NOT NULL,
  provider_activity_id TEXT CHECK(provider_activity_id IS NULL OR length(provider_activity_id) BETWEEN 1 AND 256),
  fingerprint TEXT NOT NULL CHECK(length(fingerprint) BETWEEN 1 AND 256),
  activity_type TEXT NOT NULL CHECK(activity_type IN ('earn','redeem','expire','reversal','adjustment')),
  activity_date TEXT NOT NULL,
  points_delta INTEGER NOT NULL,
  partner_id INTEGER,
  original_description TEXT CHECK(original_description IS NULL OR length(original_description) <= 2000),
  provider_updated_at TEXT,
  first_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  last_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  remote_status TEXT NOT NULL DEFAULT 'active' CHECK(remote_status IN ('active','gone')),
  CHECK(last_seen_at >= first_seen_at),
  UNIQUE(connection_id, fingerprint),
  UNIQUE(id, household_id),
  FOREIGN KEY(connection_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_connections(id, household_id) ON DELETE CASCADE,
  FOREIGN KEY(partner_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_partners(id, household_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_hh_loyalty_activities_provider_id
  ON module_haushaltsbuch_loyalty_activities(connection_id, provider_activity_id)
  WHERE provider_activity_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_expirations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  connection_id INTEGER NOT NULL,
  expiration_date TEXT NOT NULL,
  points INTEGER NOT NULL CHECK(points > 0),
  status TEXT NOT NULL DEFAULT 'scheduled' CHECK(status IN ('scheduled','expired','cancelled')),
  provider_updated_at TEXT,
  first_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  last_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  CHECK(last_seen_at >= first_seen_at),
  UNIQUE(connection_id, expiration_date),
  UNIQUE(id, household_id),
  FOREIGN KEY(connection_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_connections(id, household_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_loyalty_coupons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  connection_id INTEGER NOT NULL,
  provider_coupon_id TEXT CHECK(provider_coupon_id IS NULL OR length(provider_coupon_id) BETWEEN 1 AND 256),
  fingerprint TEXT NOT NULL CHECK(length(fingerprint) BETWEEN 1 AND 256),
  partner_id INTEGER,
  title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 500),
  description TEXT CHECK(description IS NULL OR length(description) <= 4000),
  valid_from TEXT,
  valid_until TEXT,
  activation_status TEXT NOT NULL DEFAULT 'available'
    CHECK(activation_status IN ('available','activated','redeemed','expired','unavailable')),
  multiplier TEXT CHECK(multiplier IS NULL OR length(multiplier) BETWEEN 1 AND 40),
  bonus_points INTEGER CHECK(bonus_points IS NULL OR bonus_points >= 0),
  condition_text TEXT CHECK(condition_text IS NULL OR length(condition_text) <= 4000),
  first_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  last_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  provider_updated_at TEXT,
  remote_status TEXT NOT NULL DEFAULT 'active' CHECK(remote_status IN ('active','gone')),
  CHECK(valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from),
  CHECK(last_seen_at >= first_seen_at),
  UNIQUE(connection_id, fingerprint),
  UNIQUE(id, household_id),
  FOREIGN KEY(connection_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_connections(id, household_id) ON DELETE CASCADE,
  FOREIGN KEY(partner_id, household_id)
    REFERENCES module_haushaltsbuch_loyalty_partners(id, household_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_hh_loyalty_coupons_provider_id
  ON module_haushaltsbuch_loyalty_coupons(connection_id, provider_coupon_id)
  WHERE provider_coupon_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_hh_loyalty_connections_scope
  ON module_haushaltsbuch_loyalty_connections(household_id, owner_member_id, provider);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_connections_sync
  ON module_haushaltsbuch_loyalty_connections(feature_enabled, sync_enabled, next_sync_at);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_sync_runs_connection
  ON module_haushaltsbuch_loyalty_sync_runs(connection_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_balances_connection
  ON module_haushaltsbuch_loyalty_balances(connection_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_activities_connection
  ON module_haushaltsbuch_loyalty_activities(connection_id, activity_date DESC);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_expirations_connection
  ON module_haushaltsbuch_loyalty_expirations(connection_id, expiration_date);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_partners_scope
  ON module_haushaltsbuch_loyalty_partners(household_id, provider, name);
CREATE INDEX IF NOT EXISTS idx_hh_loyalty_coupons_connection
  ON module_haushaltsbuch_loyalty_coupons(connection_id, valid_until, activation_status);
