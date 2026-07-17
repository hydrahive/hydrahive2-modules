# Haushaltsbuch — Dummy-Modul V0.1

## Was

Ein installierbares HydraHive-Cockpit-Modul als sichtbares Fundament für ein späteres Haushaltsbuch. Es stellt einen eigenen Cockpit-Reiter, eine klar als Platzhalter markierte Übersichtsseite und einen authentifizierten Status-Endpunkt bereit.

Die Übersichtsseite zeigt vier geplante Bereiche:

1. Buchungen & Budgets
2. Bankimport
3. Lidl Plus
4. PAYBACK

## Warum

Das Modul soll früh im Modul-Hub installierbar und im Cockpit sichtbar sein, ohne noch nicht implementierte Bank- oder Kundenkartenfunktionen vorzutäuschen. Spätere Etappen können auf stabiler Modul-ID, Route, Navigation und API-Basis aufbauen.

## Wie

- Modul-ID und Route: `haushaltsbuch` / `/haushaltsbuch`
- Version: `0.1.0`
- Cockpit-Topmenü über `cockpit: true`
- Backend: `GET /api/modules/haushaltsbuch/status`
- Status aller vier Bereiche: `planned`
- keine Datenbank, Credentials, externen Requests oder Hintergrunddienste
- keine Fake-Daten und keine funktionslosen Aktionsbuttons
- deutsche und englische Texte im Modul registrieren

## Akzeptanzkriterien

- Das Modul ist über `hub.json` auffindbar und installierbar.
- Nach Installation erscheint „Haushaltsbuch“ als eigener Cockpit-Reiter.
- `/haushaltsbuch` rendert innerhalb von `CockpitShell` und `CockpitTopbar`.
- Alle vier geplanten Bereiche sind sichtbar und eindeutig als „Bald verfügbar“ markiert.
- Der Status-Endpunkt verlangt Authentifizierung und meldet Modulzustand `dummy`.
- Es werden keine echten Bank-, Lidl-Plus- oder PAYBACK-Verbindungen aufgebaut.
- Backend-Test, TypeScript-Build und Modul-Hub-Validierung sind grün.

## Nicht Bestandteil von V0.1

- Buchungs- oder Budgetdaten speichern
- CSV-, MT940- oder CAMT-Import
- Bank-/FinTS-/PSD2-Anbindung
- Lidl-Plus-Login oder API-Aufrufe
- PAYBACK-Login oder API-Aufrufe
- Credentials oder personenbezogene Finanzdaten
