# Plan: Haushaltsbuch-Dummy V0.1

## Ziel

Ein installierbares Cockpit-Dummy-Modul mit vier geplanten Bereichen und authentifiziertem Status-Endpunkt.

## Dateien

- `hub.json` — Modul im Hub registrieren
- `haushaltsbuch/manifest.json` — Metadaten und Cockpit-Navigation
- `haushaltsbuch/backend/__init__.py` — Status-Endpunkt und `register(ctx)`
- `haushaltsbuch/tests/test_status.py` — Auth- und Response-Vertrag
- `haushaltsbuch/frontend/index.tsx` — Route, Navigation und i18n
- `haushaltsbuch/frontend/HaushaltsbuchPage.tsx` — Cockpit-Platzhalterseite

## Implementierungsreihenfolge

### Task 1: Backend-Vertrag

- [ ] Status-Routentest für `dummy` und vier `planned`-Bereiche schreiben
- [ ] Authentifizierung im Routentest prüfen
- [ ] minimalen Router und `register(ctx)` implementieren
- [ ] Tests grün ausführen

### Task 2: Modulregistrierung

- [ ] Manifest mit Version `0.1.0`, Route-Icon und Cockpit-Gruppe erstellen
- [ ] `haushaltsbuch` in `hub.json` aufnehmen
- [ ] JSON-Syntax und Hub-Pfade prüfen

### Task 3: Cockpit-Frontend

- [ ] Route, Cockpit-Navigation und DE/EN-i18n registrieren
- [ ] Seite mit CockpitShell/CockpitTopbar und vier geplanten Bereichen bauen
- [ ] keine anklickbaren Fake-Aktionen hinzufügen
- [ ] TypeScript-Build gegen den Core ausführen

### Task 4: Abschluss

- [ ] Security-Sanity: keine Secrets, externen Requests oder personenbezogenen Daten
- [ ] Dateien und Git-Diff reviewen
- [ ] PR erstellen und nur bei grüner CI mergen

## Nicht in diesem Plan

Echte Persistenz, Bankimporte, Banking-APIs, Lidl Plus, PAYBACK und Credentials.
