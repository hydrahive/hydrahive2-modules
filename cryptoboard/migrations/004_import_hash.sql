-- Cryptoboard — Duplikat-Schutz für CSV-Importe. Additiv, IF NOT EXISTS.
-- import_hash identifiziert eine importierte Transaktion eindeutig (aus
-- coin/kind/menge/preis/datum gebildet). Ein zweiter Import derselben Zeile
-- wird so übersprungen statt doppelt angelegt. NULL bei manuell erfassten.
ALTER TABLE module_cryptoboard_transactions ADD COLUMN import_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_cryptoboard_tx_import_hash
    ON module_cryptoboard_transactions("user", import_hash);
