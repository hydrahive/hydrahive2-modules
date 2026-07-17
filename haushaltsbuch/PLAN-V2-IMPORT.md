# Plan: Haushaltsbuch Etappe 2 — Bankimport-Inbox

## Ziel

Das Haushaltsbuch kann CAMT-V2/V8-XML, MT940-Text und konfigurierbare CSV-Bankexporte als persistenten Entwurf einlesen, prüfen, kategorisieren, atomar in den V1-Ledger übernehmen und als Importpaket stornieren.

## Dateien

### Dokumentation

- `SPEC-V2-IMPORT.md` — verbindlicher Produkt-, Daten- und Sicherheitsvertrag
- `PLAN-V2-IMPORT.md` — TDD-Implementierungsfolge
- `ROADMAP.md` — Etappe-2-Status nach Abschluss

### Backend

- `migrations/002_bank_import.sql` — Profile, Importpakete, Importzeilen, Constraints und Indizes
- `backend/import_models.py` — Pydantic-Verträge für Profile, Zeilenänderung und Abschluss
- `backend/import_parsers.py` — gemeinsames Parser-Interface und Formaterkennung
- `backend/import_camt.py` — sicherer namespace-unabhängiger CAMT.053-V2/V8-Parser
- `backend/import_mt940.py` — MT940-Parser
- `backend/import_csv.py` — CSV-Parser mit explizitem Mapping
- `backend/import_service.py` — Persistenz, Fingerprints, Duplikate, Abschluss und Storno
- `backend/routes_imports.py` — authentifizierte Multipart- und Inbox-Endpunkte
- `backend/__init__.py` — Importrouter registrieren und Status aktualisieren

### Tests

- `tests/fixtures/camt-v2.xml` — minimale synthetische CAMT-V2-Datei
- `tests/fixtures/camt-v8.xml` — fachlich gleiche CAMT-V8-Datei
- `tests/fixtures/transactions.mt940` — synthetischer MT940-Export
- `tests/fixtures/transactions.csv` — synthetischer semikolongetrennter Bankexport
- `tests/test_import_parsers.py` — Parser, Formaterkennung, Grenzen und XML-Sicherheit
- `tests/test_import_api.py` — Auth, Isolation, Inbox, Duplikate, atomarer Abschluss und Storno
- `tests/conftest.py` — Importrouter und neue Tabellen in Testreset aufnehmen

### Frontend

- `frontend/types.ts` — Importprofile, Pakete, Zeilen und Mapping
- `frontend/api.ts` — Multipart-Upload und Import-CRUD
- `frontend/HaushaltsbuchPage.tsx` — Importbereich in Navigation
- `frontend/ImportsView.tsx` — Inbox/Historie und Detailsteuerung
- `frontend/ImportUploadDialog.tsx` — Datei, Konto, Format und CSV-Mapping
- `frontend/ImportBatchView.tsx` — Vorschau, Filter, Kategorie und Zeilenentscheidungen
- `frontend/ImportHistory.tsx` — abgeschlossene/stornierte Pakete

## Implementierungsreihenfolge

### Task 1: Persistenz und Parservertrag

- [ ] Tests für Migration, Limits und Formaterkennung schreiben
- [ ] Tests rot ausführen
- [ ] `002_bank_import.sql`, Parserdatentyp und Erkennung implementieren
- [ ] Tests grün ausführen
- [ ] Commit: `feat(haushaltsbuch): add bank import foundation`

### Task 2: CAMT V2/V8

- [ ] Tests mit fachlich gleichen V2-/V8-Fixtures und Entity-Angriff schreiben
- [ ] Tests rot ausführen
- [ ] sicheren namespace-unabhängigen CAMT-Parser implementieren
- [ ] Datum, Betrag, Währung, Gegenpartei, Zweck, maskierte Kennung und Referenz normalisieren
- [ ] Tests grün ausführen
- [ ] Commit: `feat(haushaltsbuch): parse CAMT bank exports`

### Task 3: MT940 und CSV

- [ ] MT940- und CSV-Tests einschließlich cp1252, deutschem Dezimalwert und Soll/Haben schreiben
- [ ] Tests rot ausführen
- [ ] MT940-Tags und mehrzeilige Verwendungszwecke implementieren
- [ ] CSV-Mapping, Zeichensatz, Trennzeichen und Datumsformat implementieren
- [ ] Tests grün ausführen
- [ ] Commit: `feat(haushaltsbuch): parse MT940 and CSV exports`

### Task 4: Persistente Inbox und Duplikate

- [ ] API-Tests für Upload ohne Ledger-Mutation, Datei-Hash, starke/schwache Fingerprints und 404-Isolation schreiben
- [ ] Tests rot ausführen
- [ ] Upload, Normalisierung und Entwurfspersistenz implementieren
- [ ] Profil-CRUD und Zeilenänderungen mit Revision implementieren
- [ ] Tests grün ausführen
- [ ] Commit: `feat(haushaltsbuch): add persistent import inbox`

### Task 5: Atomarer Abschluss und Storno

- [ ] Tests für Kategoriepflicht, ausgeglichene Buchungen, All-or-nothing, Importreferenz und Doppelstorno schreiben
- [ ] Tests rot ausführen
- [ ] akzeptierte Zeilen über vorhandene Ledger-Invarianten atomar buchen
- [ ] paketweises Storno über Gegenbuchungen implementieren
- [ ] Audit und Revisionen integrieren
- [ ] Tests grün ausführen
- [ ] Commit: `feat(haushaltsbuch): finalize and reverse imports atomically`

### Task 6: Frontend-Upload und CSV-Mapping

- [ ] Frontend-Verträge und Multipart-API ergänzen
- [ ] Importnavigation und Uploaddialog bauen
- [ ] CSV-Header lokal lesen und Profil-/Spaltenzuordnung darstellen
- [ ] Loading-, Format-, Größen- und Parserfehler darstellen
- [ ] Typecheck ausführen
- [ ] Commit: `feat(haushaltsbuch): add bank import upload flow`

### Task 7: Inbox und Historie

- [ ] Entwurfsübersicht mit Summen, Zeitraum und Statusfiltern bauen
- [ ] Kategorie, Korrekturen und Annehmen/Verwerfen integrieren
- [ ] Abschlussdialog und Erfolgsergebnis bauen
- [ ] Historie, Details und bestätigtes Paketstorno bauen
- [ ] Typecheck und Produktionsbuild ausführen
- [ ] Commit: `feat(haushaltsbuch): build import inbox workflow`

### Task 8: Abschlussprüfung

- [ ] vollständige Haushaltsbuch-Test-Suite
- [ ] Ruff für das Modul
- [ ] Frontend-Typecheck im Core-Kontext
- [ ] Produktionsbuild
- [ ] Security-Review für Upload, XML, Haushaltsisolation, Beträge und SQL
- [ ] Browser-Smoke mit CAMT-V8- und CSV-Beispiel
- [ ] ROADMAP und Manifest aktualisieren
- [ ] PR erstellen, prüfen und erst bei grüner Verifikation mergen

## Akzeptanzkriterien

Die verbindlichen Kriterien stehen in `SPEC-V2-IMPORT.md`. Zusätzlich gilt:

- V1-Daten und manuelle Buchungen bleiben migrations- und API-kompatibel.
- Kein Upload erzeugt vor explizitem Abschluss Finanzbuchungen.
- Es werden keine Originaldateien oder vollständigen IBAN/BIC persistiert.
- Der Import ist für die konkret angebotenen CAMT-V2/V8-, MT940- und CSV-Varianten geeignet.

## Nicht in diesem Plan

- automatische Bankverbindung oder Synchronisation
- Regeln/KI-Kategorisierung
- OCR/Belege
- automatische FX-Kurse
- Hintergrundjobs
