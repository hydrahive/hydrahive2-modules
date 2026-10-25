-- VoIP Etappe 3 (PLAN-ANRUFEN-3.md): HydraHive ruft selbst an.
-- Richtung je Anruf; Zielnummer nur maskiert wie eingehend (Spalte number). Die volle Nummer wird nie gespeichert.
ALTER TABLE module_telephony_calls ADD COLUMN direction TEXT NOT NULL DEFAULT 'in';               -- in | out
-- Freigaben für Sondernummern (0900, 0137, 118xx, Satellit …) und Ausland – Standard gesperrt. Notruf ist nie wählbar.
ALTER TABLE module_telephony_connections ADD COLUMN allow_premium INTEGER NOT NULL DEFAULT 0;
ALTER TABLE module_telephony_connections ADD COLUMN allow_foreign INTEGER NOT NULL DEFAULT 0;
