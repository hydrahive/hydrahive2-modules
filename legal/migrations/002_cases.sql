-- Recht-Modul L2: Fall = Projekt (legal/SPEC-LEGAL.md §4.2, PLAN-L2.md). Alles in der DB, nichts im Projektordner.
CREATE TABLE IF NOT EXISTS module_legal_cases (
  project_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  area TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'waiting', 'done')),
  state TEXT NOT NULL,                         -- Bundesland-Kürzel für Feiertage (§ 193 BGB)
  summary TEXT NOT NULL DEFAULT '',
  facts TEXT NOT NULL DEFAULT '',
  goal TEXT NOT NULL DEFAULT '',
  our_ref TEXT NOT NULL DEFAULT '',
  their_ref TEXT NOT NULL DEFAULT '',
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  orphaned_at TEXT                             -- Projekt gelöscht: ab wann (Aufräumen nach 30 Tagen)
);

CREATE TABLE IF NOT EXISTS module_legal_parties (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES module_legal_cases(project_id),
  role TEXT NOT NULL CHECK(role IN ('opponent', 'lawyer', 'authority', 'court', 'witness', 'me', 'other')),
  name TEXT NOT NULL,
  address TEXT NOT NULL DEFAULT '',
  contact TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS module_legal_parties_case ON module_legal_parties(project_id);

CREATE TABLE IF NOT EXISTS module_legal_deadlines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES module_legal_cases(project_id),
  label TEXT NOT NULL,
  event_date TEXT NOT NULL,
  kind TEXT NOT NULL,
  amount INTEGER NOT NULL,
  start_rule TEXT NOT NULL DEFAULT 'event',
  due_date TEXT NOT NULL,
  calc TEXT NOT NULL DEFAULT '{}',             -- JSON: Rechenweg + Hinweise (deadlines.compute)
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'done', 'missed')),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS module_legal_deadlines_case ON module_legal_deadlines(project_id, due_date);

CREATE TABLE IF NOT EXISTS module_legal_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES module_legal_cases(project_id),
  author TEXT NOT NULL CHECK(author IN ('agent', 'user')),
  author_name TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  citations TEXT NOT NULL DEFAULT '[]',        -- JSON: [{citation, found}]
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS module_legal_notes_case ON module_legal_notes(project_id);

CREATE TABLE IF NOT EXISTS module_legal_proposals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES module_legal_cases(project_id),
  kind TEXT NOT NULL CHECK(kind IN ('party', 'deadline', 'fact')),
  payload TEXT NOT NULL,                       -- JSON, wie es beim Übernehmen gespeichert würde
  author_name TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'accepted', 'rejected')),
  created_at TEXT NOT NULL,
  decided_by TEXT,
  decided_at TEXT
);
CREATE INDEX IF NOT EXISTS module_legal_proposals_case ON module_legal_proposals(project_id, status);
