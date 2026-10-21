-- Mailbox M2 (PLAN-M2.md): Versand-Zählung je Konto – ohne Inhalt, nur Zeitpunkt und Anzahl Empfänger.
-- Entwürfe enthalten Mailinhalt und liegen deshalb im eigenen Index (backend/index_db.py), nicht in der Kern-DB.
CREATE TABLE IF NOT EXISTS module_mailbox_sendlog (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,
  sent_at REAL NOT NULL,                      -- Unix-Zeit
  recipients INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS module_mailbox_sendlog_acc ON module_mailbox_sendlog(account_id, sent_at);
