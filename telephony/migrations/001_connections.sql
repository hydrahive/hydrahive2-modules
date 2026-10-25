-- VoIP Etappe 1 (PLAN-EINSTELLUNGEN.md): eine SIP-Verbindung je Nutzer. Kennwort nur verschlüsselt (backend/secrets.py).
-- Die Anbindung an Telefonie-Projekte/Mitglieder (SPEC-V1 §6) folgt später; `owner` ist dann der Übergang.
CREATE TABLE IF NOT EXISTS module_telephony_connections (
  id TEXT PRIMARY KEY,                         -- zufällige ID (secrets.token_hex)
  owner TEXT NOT NULL UNIQUE,                  -- 'user:<user_id>' – stabil, auch bei Umbenennung
  pbx TEXT NOT NULL DEFAULT 'fritzbox',        -- fritzbox | sip
  display_name TEXT NOT NULL DEFAULT 'HydraHive',
  registrar TEXT NOT NULL,                     -- fritz.box oder private IPv4
  registrar_port INTEGER NOT NULL DEFAULT 5060,
  username TEXT NOT NULL,
  secret TEXT NOT NULL,                        -- verschlüsselt, nie im Klartext, nie zurückgegeben
  own_number TEXT NOT NULL DEFAULT '',
  local_sip_port INTEGER NOT NULL DEFAULT 5070,
  rtp_port_min INTEGER NOT NULL DEFAULT 7078,
  rtp_port_max INTEGER NOT NULL DEFAULT 7109,
  register_interval INTEGER NOT NULL DEFAULT 300,
  enabled INTEGER NOT NULL DEFAULT 0,          -- 1 = „Verbinden“ gedrückt: nach Neustart wieder verbinden
  status TEXT NOT NULL DEFAULT 'disconnected',
  status_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
