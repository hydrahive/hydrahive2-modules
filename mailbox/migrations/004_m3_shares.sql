-- Mailbox M3a (PLAN-M3a.md): Freigabe eines Kontos für ein Projekt (oder den eigenen Buddy) und Protokoll der
-- Agenten-Aktionen. Das Protokoll enthält nie Mailinhalt – nur wer, wo, welches Werkzeug, welche Mail-ID, Ergebnis.
CREATE TABLE IF NOT EXISTS module_mailbox_shares (
  account_id TEXT NOT NULL REFERENCES module_mailbox_accounts(id),
  target TEXT NOT NULL,                       -- 'project:<id>' | 'buddy'
  level TEXT NOT NULL DEFAULT 'read',         -- read (M3a) | draft (M3b) | send (M4)
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (account_id, target)
);
CREATE INDEX IF NOT EXISTS module_mailbox_shares_target ON module_mailbox_shares(target);

CREATE TABLE IF NOT EXISTS module_mailbox_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  username TEXT NOT NULL,
  project_id TEXT NOT NULL DEFAULT '',
  agent_id TEXT NOT NULL DEFAULT '',
  account_id TEXT NOT NULL DEFAULT '',
  tool TEXT NOT NULL,
  message_id INTEGER,
  result TEXT NOT NULL                        -- ok | denied | not_found | error
);
CREATE INDEX IF NOT EXISTS module_mailbox_audit_acc ON module_mailbox_audit(account_id, at);
