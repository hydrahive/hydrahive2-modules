# Plan: Tickets V2.1 Operations und SLA

## Ziel

Nach diesem Plan besitzt das Ticketsystem automatische, editierbare SLA-Fälligkeiten,
operative Kennzahlen, gespeicherte Ansichten, sichere Bulk-Aktionen und idempotente
interne Eskalationsbenachrichtigungen.

## Aktueller Stand

Die SLA-Domain, automatische/manuelle Fälligkeiten, Due-Date-Filter, Dashboard-
Kennzahlen, gespeicherte Ansichten, permission-geprüfte Bulk-Aktionen, idempotente
SLA-Benachrichtigungen sowie die erste Dashboard-/Fälligkeitsansicht im Frontend
sind implementiert. SLA-Profilverwaltung, vollständiger View-CRUD, Bulk-UI und die
abschließende V2-Abnahme folgen.

## Dateien

- `migrations/002_operations.sql` — SLA-, Fälligkeits- und gespeicherte-Ansichten-Schema
- `backend/sla.py` — SLA-Profilauflösung und Fälligkeitsberechnung
- `backend/service.py` — Ticket-Fristen, Bulk-Änderungen und SLA-Ereignisse
- `backend/dashboard.py` — rechtegefilterte Operationskennzahlen
- `backend/views.py` — gespeicherte Ansichten
- `backend/operations_routes.py` — Dashboard-, View-, SLA- und Bulk-Endpunkte
- `backend/routes.py` — erweiterte Ticketfilter
- `backend/models.py` — neue Request-/Response-Modelle
- `backend/__init__.py` — Registrierung der zusätzlichen Routen und Migration
- `frontend/*.tsx` — Dashboard, Fälligkeit, Ansichten und Bulk-Aktionen
- `frontend/api.ts`, `frontend/types.ts` — typisierte V2-Verträge
- `tests/test_sla.py` — Fristen, Prioritäten, Overrides und Reset
- `tests/test_operations_routes.py` — Dashboard, Ansichten, Bulk- und SLA-Rechte
- `tests/test_notifications.py` — idempotente Eskalationsbenachrichtigungen

## Implementierungsreihenfolge

### Task 1: SLA-Domain und Migration

- [x] Tests schreiben: Prioritätsprofil, automatische Fristen, manuelle Overrides und Reset
- [x] Test ausführen: RED wegen fehlender Tabellen/Servicefunktionen
- [x] Implementierung: `002_operations.sql`, `backend/sla.py`, Modelle und Migrationregistrierung
- [x] Test ausführen: GREEN für UTC-Zeitpunkte und alle Prioritäten
- [x] Commit: `feat(tickets): add editable sla deadlines`

### Task 2: Ticket-Service und bestehende Filter erweitern

- [x] Tests schreiben: automatische Berechnung bei Erstellung, Update, Statuswechsel und Prioritätsänderung
- [x] Test ausführen: RED wegen fehlender Fristenfelder
- [x] Implementierung: Serviceintegration, `due_at`-Override, Reset zur SLA-Berechnung und Filter
- [x] Test ausführen: GREEN ohne V1-Regressionsfehler
- [x] Commit: `feat(tickets): integrate ticket deadlines`

### Task 3: Dashboard und gespeicherte Ansichten

- [ ] Tests schreiben: Rechtefilter, Kennzahlen, View-CRUD und deklarative Filtervalidierung
- [ ] Test ausführen: RED wegen fehlender Operationsrouten
- [ ] Implementierung: Dashboard-/View-Service und API-Routen
- [ ] Test ausführen: GREEN für Benutzer, Team-Lead und Admin
- [ ] Commit: `feat(tickets): add operations dashboard and saved views`

### Task 4: Sichere Bulk-Aktionen

- [x] Tests schreiben: Teil-Erfolg, Einzelrechteprüfung, Audit und Benachrichtigung je Änderung
- [x] Test ausführen: RED wegen fehlender Bulk-Route
- [x] Implementierung: limitierte Bulk-Payload, atomare Ticket-Einzelupdates und Ergebnisliste
- [x] Test ausführen: GREEN ohne Rechteausweitung
- [x] Commit: `feat(tickets): add permission-checked bulk updates`

### Task 5: Idempotente Erinnerungen und Eskalationen

- [x] Tests schreiben: `due_soon`, `overdue`, SLA-Verletzung und Deduplizierung je Stufe
- [x] Test ausführen: RED wegen fehlender Eskalationslogik
- [x] Implementierung: idempotenter Notification-Service ohne externen Versand
- [x] Test ausführen: GREEN bei wiederholtem Polling
- [x] Commit: `feat(tickets): add idempotent sla notifications`

### Task 6: Frontend-Operations-Ansicht

- [ ] Tests/Verträge ergänzen: API-Typen, Filter, Bulk-Payloads und i18n-Schlüssel
- [ ] Implementierung: Dashboard-Karte, Fälligkeitseditor, Ansichten, Mehrfachauswahl und SLA-Dialog
- [ ] Test ausführen: TypeScript, ESLint und Produktionsbuild
- [ ] Commit: `feat(tickets): add operations workflow ui`

### Task 7: Abschlussprüfung und Dokumentation

- [ ] Modul-Pytest vollständig ausführen
- [ ] Frontend-TypeScript, ESLint und Produktionsbuild ausführen
- [ ] V1-Kompatibilität und Agenten-Tools prüfen
- [ ] `SPEC-V2-OPERATIONS.md` und Akzeptanzkriterien aktualisieren
- [ ] Commit: `docs(tickets): document v2 operations acceptance`

## Akzeptanzkriterien

- [ ] Automatische SLA-Fristen werden aus Priorität und aktivem Profil berechnet.
- [ ] Manuelle Fälligkeiten sind editierbar und rücksetzbar.
- [ ] Dashboard und gespeicherte Ansichten respektieren Berechtigungen.
- [ ] Bulk-Aktionen können keine Rechte umgehen und sind vollständig auditiert.
- [ ] Wiederholte Abfragen erzeugen keine doppelten Eskalationsmeldungen.
- [ ] V1 bleibt kompatibel und alle Tests bleiben grün.

## Nicht in diesem Plan

- Arbeitszeitkalender und Feiertagsberechnung
- externe Benachrichtigungen
- KI-Klassifizierung
- GitHub-/Gitea-Synchronisation
- öffentliche Kundenportale
- Echtzeit-SSE/WebSocket
