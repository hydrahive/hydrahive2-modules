-- Mailbox M1b (PLAN-M1b.md): Einstellungen des Moduls, z. B. die Microsoft-App (Client-ID), einmal global vom Admin.
CREATE TABLE IF NOT EXISTS module_mailbox_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
