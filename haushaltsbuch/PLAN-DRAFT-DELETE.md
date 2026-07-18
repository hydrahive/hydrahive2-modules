# Plan: Fehlerhafte Importentwürfe löschen

## Ziel

Ein noch nicht gebuchtes Importpaket kann nach Bestätigung vollständig gelöscht werden. Danach darf dieselbe Datei erneut hochgeladen werden. Abgeschlossene oder stornierte Pakete bleiben unveränderlich und können nur über den bestehenden Storno-Workflow behandelt werden.

## Dateien

- `backend/import_inbox.py` — haushaltsisoliertes, revisionsgeschütztes Löschen eines Entwurfs inklusive Audit.
- `backend/import_service.py` — stabile Service-Freigabe.
- `backend/routes_imports.py` — DELETE-Endpunkt.
- `frontend/api.ts` — API-Clientmethode.
- `frontend/ImportBatchView.tsx` — Löschaktion mit Bestätigungsdialog.
- `frontend/ImportsView.tsx` — gelöschtes Paket aus Inbox und Auswahl entfernen.
- `tests/test_import_api.py` — Wiederimport sowie Schutz gebuchter Pakete testen.

## Implementierungsreihenfolge

### Task 1: Backend-Vertrag
- [x] API-Test für Löschen und erneuten Upload schreiben.
- [x] Test muss ohne DELETE-Endpunkt fehlschlagen.
- [x] Nur Entwürfe mit passender Revision löschen; Haushaltsisolation beibehalten.
- [x] Löschung auditieren und Zeilen per FK-Kaskade entfernen.
- [x] Importtests grün ausführen.

### Task 2: Cockpit-Aktion
- [x] Im Entwurf einen roten „Entwurf löschen“-Button anzeigen.
- [x] Vor der unwiderruflichen Löschung Dateiname und Folgen bestätigen lassen.
- [x] Nach Erfolg zur Inbox zurückkehren und Paket lokal entfernen.
- [x] Typecheck und Produktionsbuild ausführen.

## Akzeptanzkriterien

- [x] Paket #1 kann als Entwurf gelöscht werden.
- [x] Dieselbe unveränderte Datei kann danach erneut hochgeladen werden.
- [x] Importierte und stornierte Pakete können nicht gelöscht werden.
- [x] Fremde Haushalte erhalten weiterhin 404.
- [x] Kein Ledger-Eintrag wird durch das Löschen eines Entwurfs verändert.

## Nicht in diesem Plan

- Datumsparser-Anpassungen.
- Löschen bereits gebuchter Importhistorie.
- Automatisches Ersetzen eines bestehenden Entwurfs.
