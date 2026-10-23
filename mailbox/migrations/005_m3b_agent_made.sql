-- Mailbox M3b (PLAN-M3b.md): Herkunft von Entwürfen, die ein Agent angelegt hat. Ohne Inhalt (der liegt im Index).
-- Ein Agent darf nur Entwürfe ändern, die in DIESEM Projekt von einem Agenten angelegt wurden – nie die des Menschen.
CREATE TABLE IF NOT EXISTS module_mailbox_agent_made (
  draft_id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  scope TEXT NOT NULL,                        -- 'project:<id>' | 'buddy'
  created_at TEXT NOT NULL
);
