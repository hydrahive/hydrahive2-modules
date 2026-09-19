# Plan: Tickets V2.1 Operations und SLA

## Ziel

Nach diesem Plan besitzt das Ticketsystem automatische, editierbare SLA-Fälligkeiten,
operative Kennzahlen, gespeicherte Ansichten, sichere Bulk-Aktionen und idempotente
interne Eskalationsbenachrichtigungen.

## Aktueller Stand

Die SLA-Domain, automatische/manuelle Fälligkeiten, Due-Date-Filter, Dashboard-
Kennzahlen, SLA-Profilverwaltung, vollständiger Saved-View-CRUD, permission-
geprüfte Bulk-Aktionen, idempotente SLA-Benachrichtigungen sowie die Dashboard-,
Fälligkeits-, Saved-View-, Bulk- und Admin-SLA-UI sind implementiert. Es folgen nur
noch die abschließende V2-Abnahme und die Live-Verifikation.

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

- [x] Tests schreiben: Rechtefilter, Kennzahlen, View-CRUD und deklarative Filtervalidierung
- [x] Test ausführen: RED wegen fehlender Operationsrouten
- [x] Implementierung: Dashboard-/View-Service und API-Routen
- [x] Test ausführen: GREEN für Benutzer, Team-Lead und Admin
- [x] Commit: `feat(tickets): add operations dashboard and saved views`

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

- [x] Tests/Verträge ergänzen: API-Typen, Filter, Bulk-Payloads und i18n-Schlüssel
- [x] Implementierung: Dashboard-Karte, Fälligkeitseditor, Ansichten, Mehrfachauswahl und SLA-Dialog
- [x] Test ausführen: TypeScript, ESLint und Produktionsbuild
- [x] Commit: `feat(tickets): add operations workflow ui`

### Task 7: Abschlussprüfung und Dokumentation

- [x] Modul-Pytest vollständig ausführen
- [x] Frontend-TypeScript, ESLint und Produktionsbuild ausführen
- [x] V1-Kompatibilität und Agenten-Tools prüfen
- [x] `SPEC-V2-OPERATIONS.md` und Akzeptanzkriterien aktualisieren
- [x] Commit: `docs(tickets): document v2 operations acceptance`

## Akzeptanzkriterien

- [x] Automatische SLA-Fristen werden aus Priorität und aktivem Profil berechnet.
- [x] Manuelle Fälligkeiten sind editierbar und rücksetzbar.
- [x] Dashboard und gespeicherte Ansichten respektieren Berechtigungen.
- [x] Bulk-Aktionen können keine Rechte umgehen und sind vollständig auditiert.
- [x] Wiederholte Abfragen erzeugen keine doppelten Eskalationsmeldungen.
- [x] V1 bleibt kompatibel und alle Tests bleiben grün.

## Nicht in diesem Plan

- Arbeitszeitkalender und Feiertagsberechnung
- externe Benachrichtigungen
- KI-Klassifizierung
- GitHub-/Gitea-Synchronisation
- öffentliche Kundenportale
- Echtzeit-SSE/WebSocket
