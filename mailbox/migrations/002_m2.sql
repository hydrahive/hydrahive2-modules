-- Mailbox M2 (PLAN-M2.md): Entwürfe und Versand-Zählung. Inhalte von Entwürfen bleiben klein (Text, keine Anhänge –
-- Anhänge liegen als Datei unter <data>/mailbox/drafts/<id>/). Versand-Zählung ohne Inhalt, nur Zeitpunkt und Anzahl.
CREATE TABLE IF NOT EXISTS module_mailbox_drafts (
  id TEXT PRIMARY KEY,                        -- zufällige ID
  account_id TEXT NOT NULL REFERENCES module_mailbox_accounts(id),
  owner TEXT NOT NULL,                        -- 'user:<name>' – nur der Ersteller sieht den Entwurf
  to_addr TEXT NOT NULL DEFAULT '',
  cc_addr TEXT NOT NULL DEFAULT '',
  bcc_addr TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  mode TEXT NOT NULL DEFAULT 'new',           -- new | reply | reply_all | forward
  ref_message INTEGER,                        -- Index-ID der Ursprungsmail (Antwort/Weiterleitung)
  with_attachments INTEGER NOT NULL DEFAULT 0,  -- Weiterleiten: Anhänge des Originals mitnehmen
  server_folder TEXT NOT NULL DEFAULT '',     -- Entwürfe-Ordner auf dem Server, falls abgelegt
  server_uid INTEGER,                         -- UID des Server-Entwurfs (wird beim Ändern ersetzt)
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS module_mailbox_drafts_owner ON module_mailbox_drafts(owner, updated_at);

CREATE TABLE IF NOT EXISTS module_mailbox_sendlog (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,
  sent_at REAL NOT NULL,                      -- Unix-Zeit
  recipients INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS module_mailbox_sendlog_acc ON module_mailbox_sendlog(account_id, sent_at);
