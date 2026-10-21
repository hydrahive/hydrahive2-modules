-- Mailbox M1 (mailbox/SPEC.md §4, PLAN-M1.md „zwei Datenbanken“): nur Kleines und Unersetzliches in der Kern-DB.
-- Nachrichten, Ordner und Volltext liegen im eigenen Index <archiv>/index.sqlite (backend/index_db.py).
CREATE TABLE IF NOT EXISTS module_mailbox_accounts (
  id TEXT PRIMARY KEY,                        -- zufällige ID (secrets.token_hex)
  owner TEXT NOT NULL,                        -- 'user:<name>' (M3: auch 'group:<id>')
  label TEXT NOT NULL,                        -- Anzeigename des Kontos
  address TEXT NOT NULL,                      -- Mailadresse
  sender_name TEXT NOT NULL DEFAULT '',
  auth TEXT NOT NULL DEFAULT 'password',      -- password | oauth_google | oauth_microsoft (M1b)
  imap_host TEXT NOT NULL,
  imap_port INTEGER NOT NULL DEFAULT 993,
  imap_tls TEXT NOT NULL DEFAULT 'ssl',       -- ssl | starttls
  smtp_host TEXT NOT NULL DEFAULT '',
  smtp_port INTEGER NOT NULL DEFAULT 465,
  smtp_tls TEXT NOT NULL DEFAULT 'ssl',
  username TEXT NOT NULL,
  secret TEXT NOT NULL,                       -- verschlüsselt (backend/secrets.py), nie im Klartext
  signature TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'new',         -- new | ok | auth_failed | error
  status_detail TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS module_mailbox_accounts_owner ON module_mailbox_accounts(owner);

CREATE TABLE IF NOT EXISTS module_mailbox_sync (
  account_id TEXT PRIMARY KEY REFERENCES module_mailbox_accounts(id),
  running INTEGER NOT NULL DEFAULT 0,
  started_at TEXT,
  finished_at TEXT,
  folders_total INTEGER NOT NULL DEFAULT 0,
  folders_done INTEGER NOT NULL DEFAULT 0,
  messages_total INTEGER NOT NULL DEFAULT 0,
  messages_done INTEGER NOT NULL DEFAULT 0,
  last_error TEXT NOT NULL DEFAULT ''
);
