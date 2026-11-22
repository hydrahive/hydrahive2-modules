# Zieldokument: Vault-Daten für Agenten nur bei entsperrtem Vault

> **Status:** FREIGEGEBEN (Till, 22.11.2026: „ok freigegeben“)
> **Ersetzt:** `docs/specs/vault.md` (Kern) §3 „Grundsatz“, §4.1 „Agenten-Werkzeuge laufen ohne PIN“, §8.1 (Entscheidung vom 12.10.2026)
> **Auslöser:** Till, 22.11.2026: „nur bei entsperrtem Vault laufen … für unterwegs gibt es nur Tailscale. WhatsApp ist nur
> Kommunikation, aber keinerlei Finanz- oder Gesundheitsdaten. Das gilt für alle Bereiche.“

## 1. Regeln
1. **Vault-Werkzeuge** sind alle Agenten-Werkzeuge, die Daten aus einem Vault-Bereich lesen oder ändern:
   Finanzen (Cryptoboard-Portfolio, Haushaltsbuch), Gesundheit (Patientenakte, Health), Recht (Legal).
   Maßgeblich ist die Liste im Kern plus `sensitive_tools` aus den Manifesten der Vault-Module (`"vault": true`).
   Öffentliche Daten (Krypto-Kurse, technische Analyse) gehören nicht dazu.
2. **Gesperrt = keine Daten.** Ist der Vault des Besitzers gesperrt, liefert ein Vault-Werkzeug keine Daten,
   sondern einen festen Hinweis: „Vault gesperrt – bitte in HydraHive entsperren.“ Der Agent bittet den Nutzer darum.
3. **Entsperren nur in der Oberfläche** (lokal oder über Tailscale). Die PIN wird nie im Chat abgefragt oder angenommen.
   Nach dem Entsperren dürfen die Agenten des Nutzers lesen, solange der Vault offen ist: 15 Minuten seit der
   letzten Vault-Nutzung, höchstens 8 Stunden (dieselbe Uhr wie die Oberfläche). Sperren in der Oberfläche
   sperrt auch die Agenten sofort.
4. **Externe Kanäle nie:** Läuft der Agent für eine Nachricht aus WhatsApp, Discord, Telegram, E-Mail oder einem
   anderen Kommunikationskanal, liefern Vault-Werkzeuge **nie** Daten, auch nicht bei entsperrtem Vault und auch
   nicht mit Ausnahme (Regel 5). Hinweis: „Diese Daten gibt es nur in HydraHive, nicht über <Kanal>.“
5. **Ausnahme für Auswertungen:** Pro Agent gibt es die Einstellung „Darf Vault-Daten auch bei gesperrtem Vault
   lesen“. Nur der Besitzer selbst kann sie setzen (kein anderer Nutzer, kein Agent, kein Werkzeug). Standard: aus.
   Gedacht für geplante Auswertungen (Jobs, Intervalle).
6. **Protokoll:** Jeder Aufruf eines Vault-Werkzeugs wird festgehalten: wann, welcher Agent, welches Werkzeug,
   Ergebnis (geliefert / gesperrt / Kanal abgelehnt / per Ausnahme). Keine Inhalte, keine Beträge, keine Befunde.
   Der Nutzer sieht seine Einträge im Vault-Cockpit. (Hinweis: Das Protokoll der alten Spec, V2/V3, existiert im
   Code noch nicht – keine Tabelle `vault_audit`.)
7. **Unverändert** (nicht Teil dieser Änderung): Benutzung von Zugangsdaten durch Agenten (`fetch_url` mit
   Credential, Webmin, SMB), API-Keys für Skripte, automatische Importe (Health-Ingest), Mail-Werkzeuge.

## 2. Nicht-Ziele
- Keine Verschlüsselung der Daten mit der PIN.
- Kein Entsperren per Chat, Sprachbefehl oder Link aus einem Kanal.

## 3. Abnahme-Punkte
| # | Prüfung |
|---|---|
| V1 | Vault gesperrt → `query_portfolio`, `query_fhir_data`, `query_health_data` und die Legal-Werkzeuge liefern keine Daten, sondern den Sperr-Hinweis (Test mit echtem Werkzeug-Aufruf, Gegenprobe ohne Fix rot) |
| V2 | Vault in der Oberfläche entsperrt → dieselben Werkzeuge liefern Daten; nach Sperren oder Ablauf wieder gesperrt (Test mit Zeit) |
| V3 | Lauf aus externem Kanal (WhatsApp/Discord/Mail/Telegram) → nie Daten, auch entsperrt und mit Ausnahme (Test je Kanal) |
| V4 | Ausnahme-Einstellung: nur der Besitzer kann sie setzen (API-Test mit fremdem Nutzer und per Agenten-Werkzeug → abgelehnt); mit Ausnahme liefert ein Hintergrund-Lauf bei gesperrtem Vault Daten |
| V5 | Öffentliche Werkzeuge (`query_crypto_price`, `query_crypto_analysis`) laufen weiter ohne Entsperren |
| V6 | Protokoll: jeder Aufruf ergibt einen Eintrag ohne Inhalte; Ansicht im Vault-Cockpit |
| V7 | Spec `docs/specs/vault.md` und Hilfe-Artikel (Vault, Cryptoboard, Patientenakte, Legal, Buddy) auf die neue Regel gebracht |
| V8 | Live auf dem Server: Buddy im Web gesperrt → Hinweis, entsperrt → Daten; Buddy über WhatsApp → nie Daten |
