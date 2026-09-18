# Plan: Internes HydraHive-Ticketsystem V1

## Ziel

Nach diesem Plan existiert ein natives Modul `tickets` mit internen Tickets,
Teamzuweisung, Kommentaren, Anhängen, Audit-Historie, Benachrichtigungen,
Projekt-/Task-/Session-Verknüpfungen und Agenten-Tools. Es gibt keine externe
Kunden- oder E-Mail-Funktion.

## Dateien

- `manifest.json` — Modulmetadaten, Navigation und Core-Kompatibilität
- `backend/__init__.py` — Router-, Tool- und Migrationsregistrierung
- `backend/models.py` — Request-/Response-Modelle und Wertebereiche
- `backend/permissions.py` — Admin-, Team-Lead- und Ticketzugriffsprüfungen
- `backend/service.py` — transaktionale Ticket-, Kommentar-, Team- und Auditlogik
- `backend/attachments.py` — validierter, UUID-basierter Dateispeicher
- `backend/routes.py` — authentifizierte REST-Routen
- `backend/tools/read.py` — `ticket_list` und `ticket_read`
- `backend/tools/write.py` — `ticket_create`, `ticket_comment`, `ticket_update`, `ticket_create_task`
- `migrations/001_tickets.sql` — additive Tabellen, Indizes und Sequenz
- `frontend/index.tsx` — Route, Navigation und i18n-Registrierung
- `frontend/api.ts` — typisierte HTTP-Aufrufe
- `frontend/types.ts` — gemeinsame Frontendtypen
- `frontend/TicketsPage.tsx` — Inbox und Detailzustand
- `frontend/TicketList.tsx` — Suche, Filter und Liste
- `frontend/TicketDetail.tsx` — Verlauf, Metadaten, Zuweisung und Kommentar
- `frontend/TicketForm.tsx` — Erstellen und Bearbeiten
- `frontend/TeamSettings.tsx` — Teamverwaltung für berechtigte Benutzer
- `frontend/Notifications.tsx` — interne ungelesene Meldungen
- `tests/conftest.py` — isolierte Modul-Datenbank und Auth-Fixtures
- `tests/test_migrations.py` — Schema und Indizes
- `tests/test_service.py` — Domainlogik und Statusübergänge
- `tests/test_permissions.py` — Ticket-/Teamrechte
- `tests/test_routes.py` — REST-Verträge und Fehlerfälle
- `tests/test_tools.py` — Agenten-Tools und Kontextgrenzen
- `tests/test_attachments.py` — Größen-, Pfad- und Downloadschutz

## Implementierungsreihenfolge

### Task 1: Modulgerüst und Datenbankschema

- [x] Test schreiben: Manifest, `register()`, Migration und Tabellen in `tests/test_migrations.py`
- [x] Test ausführen: die neuen Tests müssen zunächst rot sein
- [x] Implementierung: `manifest.json`, `backend/__init__.py`, `migrations/001_tickets.sql`
- [x] Test ausführen: Migration legt alle Tabellen und Indizes idempotent an
- [x] Commit: `feat: add native tickets module foundation`

### Task 2: Domainmodelle, Service und Statusworkflow

- [x] Tests schreiben: Ticketnummer, Erstellung, Filter, Statusübergänge, append-only Kommentare und Audit in `tests/test_service.py`
- [x] Test ausführen: rot wegen fehlender Servicefunktionen
- [x] Implementierung: `backend/models.py`, `backend/service.py`
- [x] Test ausführen: grün für alle gültigen und ungültigen Übergänge
- [x] Refactor: SQL-Parameter, Transaktionen und gemeinsame Validierung zentralisieren
- [x] Commit: `feat: implement ticket domain service`

### Task 3: Interne Team- und Rechteprüfung

- [x] Tests schreiben: Admin, Team-Lead, Teammitglied, Ersteller, Zugewiesener und Agentenkontext in `tests/test_permissions.py`
- [x] Test ausführen: rot wegen fehlender Prüfungen
- [x] Implementierung: `backend/permissions.py` auf Basis der bestehenden HydraHive-Rolle und Modul-Teammitgliedschaft
- [x] Test ausführen: kein Zugriff auf nicht erlaubte Änderungen; Lesen/Kommentieren gemäß V1-Vertrag
- [x] Commit: `feat: enforce internal ticket permissions`

### Task 4: REST-API für Tickets, Kommentare und Teams

- [x] Tests schreiben: CRUD, Filter/Pagination, Kommentarverlauf, Teams, Statusfehler und Auth in `tests/test_routes.py`
- [x] Test ausführen: rot
- [x] Implementierung: Pydantic-Bodies und `backend/routes.py`
- [x] Test ausführen: grün mit stabilen HTTP-Statuscodes und ohne interne Fehlerdetails
- [x] Commit: `feat: expose ticket REST api`

### Task 5: Anhänge und Audit-Nebenwirkungen

- [x] Tests schreiben: 25-MiB-Limit, erlaubter Download, zufällige Storage-Keys, Dateinamen-/Path-Traversal-Schutz in `tests/test_attachments.py`
- [x] Test ausführen: rot
- [x] Implementierung: `backend/attachments.py` und Route-Integration
- [x] Test ausführen: Upload/Download funktioniert nur über Ticketberechtigung; Originaldatei wird nie als Pfad ausgegeben
- [x] Commit: `feat: add secure internal ticket attachments`

### Task 6: Agenten-Toolschicht

- [x] Tests schreiben: kompakte Listen-/Detailantwort, User-/Agenten-Autor, Projekt-/Session-Kontext, Rechteprüfung und Task-Verknüpfung in `tests/test_tools.py`
- [x] Test ausführen: rot
- [x] Implementierung: `backend/tools/read.py`, `backend/tools/write.py` und Registrierung
- [x] Test ausführen: alle Tools verwenden ausschließlich `ToolContext` und schreiben Audit-Events
- [x] Commit: `feat: add ticket agent tools`

### Task 7: Native Frontend-Inbox und Detailansicht

- [x] Tests schreiben: TypeScript-Typen, API-Aufrufe und vorhandene Frontend-Testmuster erweitern
- [x] Test ausführen: rot wegen fehlender Komponenten
- [x] Implementierung: `frontend/index.tsx`, `api.ts`, `types.ts`, `TicketsPage.tsx`, `TicketList.tsx`, `TicketDetail.tsx`, `TicketForm.tsx`
- [x] Implementierung: interne Kommentare, Status/Priorität, Team-/Zuweisung und Projekt-/Task-Links
- [x] Test ausführen: Frontend-Produktionsbuild grün
- [x] Commit: `feat: add native tickets frontend`

### Task 8: Teams, Benachrichtigungen und Abschlussprüfung

- [x] Tests schreiben: Teamverwaltung, Benachrichtigungsquittierung, Auditdarstellung und i18n in Backend-Tests sowie Frontendvertrag
- [x] Test ausführen: rot
- [x] Implementierung: `TeamSettings.tsx`, `Notifications.tsx`, interne Notification-Servicefunktionen und i18n
- [x] Test ausführen: Modul-Pytest, TypeScript/Vite-Build, Manifest-/Spec-Guards und Sicherheitsprüfung
- [ ] Commit: `feat: complete internal ticket workflow`

### Task 9: Top-Menü-Integration

- [ ] Test/Guard: Module mit `topnav: true` werden in die vorhandenen Top-Quicklinks aufgenommen
- [ ] Implementierung: `hydrahive2/frontend/src/shared/nav-config.ts`, `hydrahive2/frontend/src/shared/Layout.tsx` und `tickets/frontend/index.tsx`
- [ ] Implementierung: Das Menü wird erweitert; bestehende Quicklinks bleiben erhalten
- [ ] Test ausführen: Frontend-Produktionsbuild grün
- [ ] Commit: `feat: show tickets in top navigation`

## Akzeptanzkriterien

- [ ] Ein authentifizierter Benutzer kann ein internes Ticket erstellen und kommentieren.
- [ ] Tickets können Teams und einzelnen Benutzern zugewiesen werden.
- [ ] Status, Priorität, Kategorie, Tags und Verknüpfungen zu Projekt/Task/Session sind bearbeitbar.
- [ ] Jeder Änderungs- und Kommentarvorgang ist nachvollziehbar auditiert.
- [ ] Anhänge sind begrenzt, nicht-destruktiv gespeichert und zugriffsgeschützt.
- [ ] Agenten können Tickets lesen, erstellen, kommentieren, aktualisieren und Tasks verknüpfen.
- [ ] Agenten erhalten keine Rechte über den Benutzerkontext hinaus.
- [ ] Die UI ist unter `/tickets` erreichbar und verwendet HydraHive-Auth/i18n.
- [ ] Es gibt keine E-Mail-Anbindung und keine externe öffentliche Ticketansicht.
- [ ] Bestehende Core- und Modul-Tests bleiben grün.

## Nicht in diesem Plan

- externe Kundenportale
- E-Mail-Eingang oder E-Mail-Versand
- osTicket-Laufzeitintegration
- öffentliche Kommentare
- Echtzeit-SSE/WebSocket
- automatische KI-Klassifizierung ohne expliziten Agentenaufruf
- Core-Änderungen am globalen Benutzerrollenmodell
