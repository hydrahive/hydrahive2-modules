-- VoIP Etappe 2a (PLAN-ANRUFE-2A.md): Anrufe annehmen mit Ansage, Testanruf, Anrufliste.
ALTER TABLE module_telephony_connections ADD COLUMN answer_calls INTEGER NOT NULL DEFAULT 0;
ALTER TABLE module_telephony_connections ADD COLUMN greeting TEXT NOT NULL DEFAULT '';
ALTER TABLE module_telephony_connections ADD COLUMN test_until TEXT;        -- offenes Testfenster (ISO-Zeit) oder NULL

-- Anrufliste: nur maskierte Nummer und Zähler – kein Ton, kein Inhalt. Höchstens 50 je Verbindung (connections.py).
CREATE TABLE IF NOT EXISTS module_telephony_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  connection_id TEXT NOT NULL REFERENCES module_telephony_connections(id) ON DELETE CASCADE,
  started_at TEXT NOT NULL,
  number TEXT NOT NULL,                        -- z. B. '•••567' oder 'unbekannt'
  result TEXT NOT NULL,                        -- answered | rejected | busy | cancelled | caller_hangup | no_ack | codec | …
  codec TEXT NOT NULL DEFAULT '',
  rtp_out INTEGER NOT NULL DEFAULT 0,
  rtp_in INTEGER NOT NULL DEFAULT 0,
  is_test INTEGER NOT NULL DEFAULT 0,
  heard INTEGER                                -- Testanruf: 1 = Ton gehört, 0 = nicht gehört, NULL = offen
);
CREATE INDEX IF NOT EXISTS module_telephony_calls_conn ON module_telephony_calls(connection_id, id);
