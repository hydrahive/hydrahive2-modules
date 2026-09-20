# Plan: GitHub Hybrid Workbench für Tickets

## Ziel

GitHub-Issues werden zentral als HydraHive-Tickets importiert und bedient. GitHub-
Issue-/Project-Felder werden kontrolliert synchronisiert; interne Ticketdaten bleiben
HydraHive-Daten.

## Dateien

- `migrations/005_github_hybrid.sql` — Snapshot-/Sync-Spalten und Indizes
- `backend/models.py` — Sync-/Write-Requests und GitHub-Datenvalidierung
- `backend/github_provider.py` — Issue-Liste, Mutationen und Project-Operationen
- `backend/github.py` — Upsert, Snapshot, Link-/Sync-Persistenz
- `backend/github_routes.py` — Import, Sync und geschützte Push-Routen
- `backend/routes.py` / `backend/service.py` — lokales Ticketverhalten unverändert wiederverwenden
- `tests/test_github_provider.py` — GraphQL-Erfolg, Fehler, Pagination und Mutationen
- `tests/test_github_sync.py` — Idempotenter Import, Rechte, Konflikte, Read-only-Gate
- `frontend/GithubWorkbench.tsx` — zentrale Ticket-/Project-Ansicht
- `frontend/GithubProjectItems.tsx` — in die Workbench integrieren oder entfernen
- `frontend/api.ts`, `frontend/types.ts`, `frontend/index.tsx`, `frontend/TicketsPage.tsx` — API, DTOs, Layout, i18n

## Implementierungsreihenfolge

### Task 1: Persistenz und DTOs
- [ ] Test schreiben: Snapshot- und Sync-Felder werden migriert und bestehen bei Wiederholung.
- [ ] Migration für `last_remote_snapshot_json`, `sync_state`, `last_synced_at`, `last_error` und sinnvolle Indizes.
- [ ] Pydantic-Modelle für Import-/Sync-/Issue-/Project-Aktionen.
- [ ] Migrationstests grün.

### Task 2: Provider-Read erweitern
- [ ] Test schreiben: Issues mit Pagination und vollständigem Snapshot werden tokenfrei zurückgegeben.
- [ ] Issue-Abfrage für OPEN/CLOSED und Filter Owner/Repository.
- [ ] Project-Items inklusive Status-/Single-Select-Feldwerte lesen.
- [ ] Rate-Limit, GraphQL-Fehler und Seitenlimit testen.

### Task 3: Idempotenter lokaler Import
- [ ] Test schreiben: derselbe externe Issue-Key erzeugt genau ein HydraHive-Ticket.
- [ ] Import erstellt oder aktualisiert Ticket + GitHub-Link in einer Transaktion.
- [ ] Snapshot und `last_synced_at` schreiben; Fehlerstatus ohne Ticketverlust.
- [ ] Bestehende HydraHive-Ticketrechte und Audit-Events verwenden.

### Task 4: Zentrale Workbench
- [ ] Test/Typecheck: Ticketliste, Detailansicht und Sync-Status.
- [ ] Sidebar-Listen entfernen; Workbench als Hauptbereich mit Tabs/Filter einbauen.
- [ ] Import-/Sync-Aktionen und Loading-/Fehler-/Konfliktzustände.
- [ ] Existing TicketDetail wiederverwenden.

### Task 5: Expliziter Push-Modus
- [ ] Test schreiben: `read_only` lehnt jede Mutation mit stabilem Fehler ab.
- [ ] Provider-Mutationen für Issue-Felder, State, Labels und Assignee.
- [ ] Verbindungseinstellung für `push`/`bidirectional` mit Projektzugriff.
- [ ] Jede Mutation auditieren und bei Fehler `sync_state=error` setzen.

### Task 6: Project-Board-Aktionen
- [ ] Test schreiben: Add/remove/move Project-Item mit Project- und Connection-Prüfung.
- [ ] Project-Statusfelder und unterstützte Single-Select-Optionen darstellen.
- [ ] Board-Ansicht mit expliziter Bestätigung für Änderungen.
- [ ] Unbekannte/unsupported Feldtypen sichtbar, aber nicht destruktiv editierbar.

### Task 7: Abschlussprüfung
- [ ] Backend-Suite und Frontend-Build ausführen.
- [ ] Security-Audit: Token-Redaction, Auth, Inputvalidierung, Write-Gate.
- [ ] Modulversion erhöhen und installierte Version aktualisieren.
- [ ] Commit/Push nach Git-Workflow und Abschlussverifikation.

## Akzeptanzkriterien

- [ ] Issues werden zentral als Tickets mit eindeutiger externer ID angezeigt.
- [ ] Wiederholter Sync ist idempotent.
- [ ] Read-only-Verbindungen bleiben schreibgeschützt.
- [ ] Hybridfelder und Konflikte sind sichtbar.
- [ ] Project-Items können gelesen und im aktivierten Push-Modus bewegt werden.
- [ ] Alle bisherigen 64+ Tests bleiben grün; neue Sync-/Provider-/Route-Tests decken Schreibschutz und Berechtigungen ab.

## Nicht in diesem Plan

- Webhook-Infrastruktur und Hintergrund-Scheduler für automatische Echtzeit-Synchronisation.
- Vollständige Spiegelung von GitHub-Kommentaren und Review-Threads.
- Pull-Request-spezifischer Workflow.
- Beliebige GitHub-API-Endpunkte außerhalb der begrenzten Issue-/Project-Operationen.
