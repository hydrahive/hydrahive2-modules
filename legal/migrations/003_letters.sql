-- Recht-Modul L3: Schriftverkehr + Brief-Vorschlag (PLAN-L3.md). Kein automatischer Versand.
CREATE TABLE IF NOT EXISTS module_legal_correspondence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES module_legal_cases(project_id),
  direction TEXT NOT NULL CHECK(direction IN ('in', 'out')),
  status TEXT NOT NULL CHECK(status IN ('draft', 'sent', 'received')),
  date TEXT NOT NULL DEFAULT '',
  sender TEXT NOT NULL DEFAULT '',
  recipient TEXT NOT NULL DEFAULT '',
  their_ref TEXT NOT NULL DEFAULT '',
  our_ref TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  delivery TEXT NOT NULL DEFAULT '',
  proof TEXT NOT NULL DEFAULT '',
  letter_type TEXT NOT NULL DEFAULT '',
  attachments TEXT NOT NULL DEFAULT '[]',     -- JSON-Liste
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS module_legal_correspondence_case ON module_legal_correspondence(project_id, date);

-- Vorschläge: kind um 'letter' erweitern. SQLite kann einen CHECK nicht per ALTER ändern → Tabelle neu anlegen und kopieren.
-- Wiederholbar: Ein Rest von einem abgebrochenen Lauf (_new) wird zuerst entfernt. Wichtig, weil der Kern-Migrator eine
-- Migration mit „already exists“ als erledigt markieren würde (modules/migrations.py) – dann bliebe der alte CHECK.
DROP TABLE IF EXISTS module_legal_proposals_new;
CREATE TABLE module_legal_proposals_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES module_legal_cases(project_id),
  kind TEXT NOT NULL CHECK(kind IN ('party', 'deadline', 'fact', 'letter')),
  payload TEXT NOT NULL,
  author_name TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'accepted', 'rejected')),
  created_at TEXT NOT NULL,
  decided_by TEXT,
  decided_at TEXT
);
INSERT INTO module_legal_proposals_new(id, project_id, kind, payload, author_name, status, created_at, decided_by, decided_at)
  SELECT id, project_id, kind, payload, author_name, status, created_at, decided_by, decided_at FROM module_legal_proposals;
DROP TABLE module_legal_proposals;
ALTER TABLE module_legal_proposals_new RENAME TO module_legal_proposals;
CREATE INDEX IF NOT EXISTS module_legal_proposals_case ON module_legal_proposals(project_id, status);
