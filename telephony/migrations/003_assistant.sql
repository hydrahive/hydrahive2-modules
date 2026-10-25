-- VoIP Etappe 2b (PLAN-AGENT-2B.md): Telefon-Assistent und Notizen.
ALTER TABLE module_telephony_connections ADD COLUMN call_mode TEXT NOT NULL DEFAULT 'greeting';   -- greeting | assistant
ALTER TABLE module_telephony_connections ADD COLUMN assistant_name TEXT NOT NULL DEFAULT '';
ALTER TABLE module_telephony_connections ADD COLUMN assistant_knowledge TEXT NOT NULL DEFAULT '';
ALTER TABLE module_telephony_connections ADD COLUMN assistant_model TEXT NOT NULL DEFAULT '';      -- '' = Standardmodell

-- Notiz je Gespräch: nur was der Anrufer selbst angegeben hat + Zusammenfassung. Kein Ton, kein Wortlaut.
ALTER TABLE module_telephony_calls ADD COLUMN turns INTEGER NOT NULL DEFAULT 0;
ALTER TABLE module_telephony_calls ADD COLUMN notes TEXT NOT NULL DEFAULT '';                     -- JSON (agent/reply.py)
ALTER TABLE module_telephony_calls ADD COLUMN notes_read INTEGER NOT NULL DEFAULT 1;               -- 0 = neue Notiz
