PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_households (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
  base_currency TEXT NOT NULL CHECK(length(base_currency) = 3),
  timezone TEXT NOT NULL,
  owner_user_id TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_members (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL UNIQUE,
  username TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('owner','member')),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  joined_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(household_id, user_id), UNIQUE(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_invites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','revoked')),
  created_by TEXT NOT NULL,
  accepted_by TEXT,
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  accepted_at TEXT,
  UNIQUE(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
  type TEXT NOT NULL CHECK(type IN ('checking','savings','cash','credit_card','wallet','liability','asset','custom','equity','rounding')),
  owner_member_id INTEGER,
  currency TEXT NOT NULL CHECK(length(currency) = 3),
  bank_identifier TEXT,
  archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
  internal INTEGER NOT NULL DEFAULT 0 CHECK(internal IN (0,1)),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(household_id, name), UNIQUE(id, household_id),
  FOREIGN KEY(owner_member_id, household_id) REFERENCES module_haushaltsbuch_members(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  parent_id INTEGER,
  name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
  kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
  icon TEXT, color TEXT, sort_order INTEGER NOT NULL DEFAULT 0,
  archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(household_id, parent_id, name), UNIQUE(id, household_id),
  FOREIGN KEY(parent_id, household_id) REFERENCES module_haushaltsbuch_categories(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  booking_date TEXT NOT NULL, value_date TEXT NOT NULL,
  counterparty TEXT, purpose TEXT, note TEXT,
  status TEXT NOT NULL DEFAULT 'posted' CHECK(status IN ('posted','reversed')),
  source TEXT NOT NULL DEFAULT 'manual' CHECK(source IN ('manual','import','receipt','lidl_plus','payback')),
  created_by TEXT NOT NULL,
  reversal_of_id INTEGER,
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(id, household_id), UNIQUE(reversal_of_id),
  FOREIGN KEY(reversal_of_id, household_id) REFERENCES module_haushaltsbuch_transactions(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_postings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  transaction_id INTEGER NOT NULL,
  account_id INTEGER,
  category_id INTEGER,
  original_amount INTEGER NOT NULL,
  currency TEXT NOT NULL CHECK(length(currency) = 3),
  base_amount INTEGER NOT NULL,
  exchange_rate TEXT,
  exchange_rate_date TEXT,
  exchange_rate_source TEXT,
  member_id INTEGER,
  CHECK((account_id IS NOT NULL) != (category_id IS NOT NULL)),
  FOREIGN KEY(transaction_id, household_id) REFERENCES module_haushaltsbuch_transactions(id, household_id) ON DELETE CASCADE,
  FOREIGN KEY(account_id, household_id) REFERENCES module_haushaltsbuch_accounts(id, household_id),
  FOREIGN KEY(category_id, household_id) REFERENCES module_haushaltsbuch_categories(id, household_id),
  FOREIGN KEY(member_id, household_id) REFERENCES module_haushaltsbuch_members(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_budgets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  category_id INTEGER,
  type TEXT NOT NULL CHECK(type IN ('monthly','monthly_rollover','reserve','one_time','yearly')),
  amount INTEGER NOT NULL CHECK(amount >= 0),
  start_date TEXT NOT NULL, end_date TEXT NOT NULL CHECK(end_date >= start_date),
  warning_threshold INTEGER NOT NULL DEFAULT 80 CHECK(warning_threshold BETWEEN 0 AND 100),
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(id, household_id),
  FOREIGN KEY(category_id, household_id) REFERENCES module_haushaltsbuch_categories(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_budget_periods (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  budget_id INTEGER NOT NULL,
  start_date TEXT NOT NULL, end_date TEXT NOT NULL,
  base_allocation_amount INTEGER NOT NULL,
  allocated_amount INTEGER NOT NULL, spent_amount INTEGER NOT NULL,
  rollover_amount INTEGER NOT NULL DEFAULT 0,
  closed_at TEXT NOT NULL,
  UNIQUE(budget_id, start_date, end_date),
  FOREIGN KEY(budget_id, household_id) REFERENCES module_haushaltsbuch_budgets(id, household_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_budget_adjustments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL,
  budget_period_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_budget_periods(id) ON DELETE CASCADE,
  transaction_id INTEGER NOT NULL,
  amount INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  FOREIGN KEY(transaction_id, household_id) REFERENCES module_haushaltsbuch_transactions(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_recurring_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
  account_id INTEGER NOT NULL, category_id INTEGER NOT NULL,
  frequency TEXT NOT NULL CHECK(frequency IN ('daily','weekly','monthly','yearly')),
  interval_count INTEGER NOT NULL DEFAULT 1 CHECK(interval_count > 0),
  next_due_date TEXT NOT NULL, end_date TEXT,
  anchor_day INTEGER CHECK(anchor_day BETWEEN 1 AND 31),
  amount INTEGER NOT NULL CHECK(amount >= 0), tolerance INTEGER NOT NULL DEFAULT 0 CHECK(tolerance >= 0),
  counterparty TEXT, cancellation_notice_days INTEGER, note TEXT,
  status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('draft','confirmed','inactive')),
  confidence TEXT NOT NULL DEFAULT '1',
  revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(id, household_id),
  FOREIGN KEY(account_id, household_id) REFERENCES module_haushaltsbuch_accounts(id, household_id),
  FOREIGN KEY(category_id, household_id) REFERENCES module_haushaltsbuch_categories(id, household_id)
);

CREATE TABLE IF NOT EXISTS module_haushaltsbuch_audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  actor_user_id TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
  action TEXT NOT NULL, before_json TEXT, after_json TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_hh_members_household ON module_haushaltsbuch_members(household_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_hh_categories_scope_name
  ON module_haushaltsbuch_categories(household_id, COALESCE(parent_id, 0), name);
CREATE INDEX IF NOT EXISTS idx_hh_postings_transaction ON module_haushaltsbuch_postings(transaction_id);
CREATE INDEX IF NOT EXISTS idx_hh_postings_account ON module_haushaltsbuch_postings(household_id, account_id);
CREATE INDEX IF NOT EXISTS idx_hh_postings_category ON module_haushaltsbuch_postings(household_id, category_id);
CREATE INDEX IF NOT EXISTS idx_hh_transactions_date ON module_haushaltsbuch_transactions(household_id, booking_date DESC);
CREATE INDEX IF NOT EXISTS idx_hh_audit ON module_haushaltsbuch_audit_events(household_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_hh_recurring_due ON module_haushaltsbuch_recurring_rules(household_id, next_due_date);
CREATE INDEX IF NOT EXISTS idx_hh_budgets_scope ON module_haushaltsbuch_budgets(household_id, category_id, start_date, end_date);
