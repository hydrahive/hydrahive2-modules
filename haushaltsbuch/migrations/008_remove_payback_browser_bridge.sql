PRAGMA foreign_keys = ON;

-- PAYBACK Browser-Bridge wurde entfernt. Nur von der Bridge erzeugte
-- Verbindungen löschen; andere providerneutrale PAYBACK-Datensätze bleiben erhalten.
DELETE FROM module_haushaltsbuch_loyalty_connections
WHERE provider = 'payback'
  AND credential_ref = 'payback-browser-bridge';

DROP TABLE IF EXISTS module_haushaltsbuch_payback_bridge_flows;
