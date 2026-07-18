# Plan: Experimenteller Lidl-Plus-Testconnector

## Ziel

Ein Nutzer kann Lidl Plus ohne Passwortübergabe per manuellem PKCE-Browserflow
verbinden, digitale Belege read-only synchronisieren und deren Artikel ansehen.

## Implementierungsreihenfolge

### Task 1: Kanonischer Belegvertrag

- [ ] Migrationstest für Auth-Flows, Belege, Positionen und Adjustments schreiben (RED)
- [ ] `migrations/005_lidl_receipts.sql` implementieren (GREEN)
- [ ] Provider-Belegmodelle und Fake-Provider-Contracttests schreiben (RED)
- [ ] `loyalty_provider.py` und `providers/fake.py` erweitern (GREEN)
- [ ] Commit: `feat(haushaltsbuch): add canonical receipt contract`

### Task 2: Lidl-Normalisierung

- [ ] Fixturetests für DE-Locale-Beträge, Artikel, Rabatte, Pfand, GTIN und Warnungen (RED)
- [ ] `lidl_normalize.py` mit `Decimal` und ohne Rohpayloadpersistenz implementieren (GREEN)
- [ ] Commit: `feat(haushaltsbuch): normalize lidl receipts safely`

### Task 3: Manueller PKCE-Flow

- [ ] Tests für S256, verschlüsselten Flow-Token, Scope/Ablauf, Callback-Allowlist,
      State-Mismatch, Replay und redigierte Fehler schreiben (RED)
- [ ] `lidl_auth.py`, Requests und Start-/Complete-Routes implementieren (GREEN)
- [ ] Refresh-Token über `save_credential`, Verbindung über vorhandene sichere
      Connection-Persistenz erzeugen
- [ ] Commit: `feat(haushaltsbuch): add guided lidl pkce connection`

### Task 4: Read-only Lidl-Adapter und Belegsync

- [ ] HTTP-Mocktests für Tokenrefresh, Rotation, Ticketpagination, 401/403/429/5xx,
      Content-Type und Größenlimit schreiben (RED)
- [ ] `providers/lidl.py` mit festen Hosts, TLS und Timeouts implementieren (GREEN)
- [ ] Belege in `_collect` und `persist_sync` integrieren; Idempotenztest (RED/GREEN)
- [ ] Adapter beim Modulstart registrieren; nur DE/de und Kill-Switch
- [ ] Commit: `feat(haushaltsbuch): sync lidl receipts read only`

### Task 5: Beleg-API

- [ ] Scope-/Mitgliedsisolation für Liste und Detail testen (RED)
- [ ] `loyalty_receipts.py` und GET-Routes implementieren (GREEN)
- [ ] Commit: `feat(haushaltsbuch): expose household scoped receipts`

### Task 6: Verbindungsassistent und Belegansicht

- [ ] Frontendtypen/API für Auth-Start, Auth-Complete, Belegliste/-detail
- [ ] `LidlConnectDialog.tsx` mit Einwilligung, externem Login-Link und Callbackfeld
- [ ] `LoyaltyReceipts.tsx` mit Artikel-/Adjustment-Detail
- [ ] Lidl-Karte freischalten, PAYBACK weiterhin geplant
- [ ] Commit: `feat(haushaltsbuch): add experimental lidl setup ui`

### Task 7: Abschluss

- [ ] Security-Audit: Secrets, Callback/SSRF, Logs, SQL, Rate-Limits, Responsegrößen
- [ ] HH-Review: Produktionsdateien max. 200 Zeilen, Grenzen und Tests
- [ ] Gesamte Pytests, Ruff, TypeScript-Typecheck und Vite-Build
- [ ] API-Contract/Status aktualisieren und Manifest-Version erhöhen
- [ ] PR mit persönlicher Testanleitung erstellen

### Task 8: Initiales Access-Token bis zum ersten Sync nutzen

- [x] Integrationstest: Auth-Complete übergibt Access-Token an den registrierten Adapter (RED)
- [x] Integrationstest: erster Sync ruft Tickets direkt und nicht den Refresh-Endpunkt auf (RED)
- [x] `ExchangeResult` um validierte Access-Token-Metadaten ergänzen
- [x] In-Memory-Handoff an die konkrete neue Connection implementieren (GREEN)
- [x] `probe()` nutzt gültige In-Memory-Tokens bis zum Ablauf; Trennen entfernt sie sofort
- [x] Test für abgelaufenes Token: sicherer Refreshpfad bleibt aktiv
- [x] Security-/HH-Review, Gesamttests, Version und Source-PR

### Task 9: Aktuellen Android-Ticketvertrag und Fehlerstufen übernehmen

- [x] Juni-2026-Referenz gegen bisherigen iOS-Headersatz vergleichen
- [x] Exakten Android-Headersatz als RED-Regressionstest abbilden
- [x] Stabile, nicht personenbezogene 16-Hex-Device-ID pro Connection ableiten
- [x] Ticket-401 einmal refreshen und denselben Request einmal wiederholen
- [x] Tokenendpoint-Ablehnung und Ticket-Ablehnung mit statischen Stage-Codes trennen
- [x] Detailcode in `ProviderError.code` statt nur im Exception-Text persistieren
- [x] Alten generischen `reauth_required/auth_required`-Zustand einmalig recovern
- [x] Security-/HH-Review, Gesamttests, Version und Source-PR

## Akzeptanzkriterien

Siehe `SPEC-V4.1-LIDL-EXPERIMENTAL.md`.

## Nicht in diesem Plan

Automatischer Login, Selenium, Schutzmaßnahmen umgehen, Rechtstexte automatisch
akzeptieren, Couponaktivierung, Schedule, OCR/PDF/E-Mail, PAYBACK und automatisches
Ledger-Matching.
