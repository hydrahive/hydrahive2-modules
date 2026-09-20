# HydraHive Tickets V3 — GitHub Projects Integration

## Ziel

HydraHive bleibt die interne Ticketzentrale. GitHub Issues, Pull Requests und
Projects werden als externer Projekt-Provider angebunden, damit Teams ihre
bestehenden GitHub-Workflows weiterverwenden können. Ein HydraHive-Ticket kann
mit genau einem GitHub Issue/Project-Item verknüpft werden; mehrere externe
Provider bleiben später möglich.

GitHub ist in V3 **nicht** die primäre Ticketdatenbank. Interne Rechte,
Audit-Historie, SLA, Anhänge und Agentenkontext bleiben in HydraHive.

## Nichtziele der ersten Lieferung

- keine vollständige Kopie der GitHub-Projects-Oberfläche
- kein ungeprüfter bidirektionaler Status-Sync
- keine Speicherung von GitHub-Tokens im Ticket- oder Projekt-Datensatz
- keine beliebigen externen GraphQL-URLs (nur `https://api.github.com/graphql`)
- keine automatische Änderung von GitHub-Issues durch jeden Agenten
- kein Webhook-Zwang für den Read-only-MVP

## Provider-Schnittstelle

Der Ticket-Code verwendet eine kleine Provider-Schnittstelle statt direkter
GitHub-Aufrufe in Routes oder Agent-Tools:

- `list_projects(connection)`
- `get_project(connection, project_id_or_number)`
- `list_project_items(connection, project_id)`
- `get_issue(connection, owner, repository, number)`
- später: `create_issue`, `update_issue`, `add_project_item`, `update_project_field`

`GitHubProjectsProvider` implementiert diese Schnittstelle über GraphQL. Die
Provider-Schicht erhält bereits aufgelöste, kurzlebige Credentials, gibt Tokens
aber nie in Exceptions, Logs oder Tool-Ergebnissen zurück.

## Verbindung und Credentials

Eine Verbindung gehört zu einem HydraHive-Projekt und enthält nur Metadaten:

- GitHub-Owner/Login
- Repository-Name
- Project-Nummer oder Project-Node-ID
- Credential-Referenz (Name im verschlüsselten HydraHive-Credential-Store)
- `enabled`
- `sync_mode`: `read_only`, später `push`, `bidirectional`
- `created_by`, `created_at`, `updated_at`

Das Credential selbst bleibt im bestehenden Credential-Store. Für den MVP wird
ein GitHub-Bearer-Token mit passendem URL-Muster verwendet. Ein Project-Token
wird nicht global aus `GH_TOKEN` des Shell-Tools übernommen; die Verbindung
muss explizit und nachvollziehbar sein.

## Verknüpfung

Eine Ticket-Verknüpfung speichert:

- `ticket_id`
- GitHub-Owner und Repository
- Issue-Nummer und Issue-Node-ID
- optional Project-Node-ID und Project-Item-ID
- externe URL
- `sync_state`: `linked`, `stale`, `error`
- `last_synced_at`, `last_error`
- `created_by`, `created_at`, `updated_at`

Eindeutigkeit: ein Ticket darf höchstens eine aktive GitHub-Verknüpfung haben;
die Kombination aus Owner, Repository und Issue-Nummer ist ebenfalls eindeutig.
Die lokale Verknüpfung darf ohne GitHub-Schreibzugriff angelegt werden, wenn das
Issue bereits existiert.

## Read-only-MVP

### API unter `/api/modules/tickets`

- `GET /github/connections` — maskierte Verbindungsmetadaten
- `POST /github/connections` — Projektverbindung anlegen/aktualisieren
- `DELETE /github/connections/{connection_id}` — Verbindung deaktivieren/löschen
- `GET /github/projects` — Projects der konfigurierten Verbindung
- `GET /github/projects/{project_id}/items` — Items kompakt lesen
- `GET /tickets/{ticket_id}/github` — Verknüpfung und letzter Sync-Status
- `POST /tickets/{ticket_id}/github/link` — bestehendes Issue lokal verknüpfen
- `DELETE /tickets/{ticket_id}/github/link` — lokale Verknüpfung lösen
- `POST /github/connections/{connection_id}/check` — Verbindung testen, ohne Secret zurückzugeben

Alle Mutationen bleiben durch HydraHive-Authentifizierung und die bestehenden
Ticket-/Projektberechtigungen geschützt. `POST .../link` darf nur ein Issue
verknüpfen, das über die API gelesen und validiert wurde.

### Agenten-Tools im MVP

Separate Tools, nicht automatisch Schreibrechte aus den bestehenden Ticket-Tools
ableiten:

- `github_project_list` — Projects/Verbindungen lesen
- `github_project_read` — Project und Items lesen
- `ticket_github_read` — externe Verknüpfung und Status lesen
- `ticket_github_link` — ein vorhandenes Issue lokal verknüpfen

`ticket_github_link` verändert GitHub nicht. Tool-Kontext, Benutzer-Identität,
Agent-ID, Session und Project-ID werden serverseitig geprüft und auditierbar
protokolliert.

## Spätere Push-/Sync-Phasen

### Push

HydraHive kann explizit ein Issue erzeugen oder ein bestehendes Issue in ein
Project aufnehmen. Jeder Schreibvorgang braucht eine eigene Berechtigung und
Bestätigung. Die Antwort speichert die zurückgegebenen GitHub-Node-IDs.

### Bidirektional

Erst nach dem Read-only-MVP und einem Outbox-/Webhook-Test:

- HydraHive bleibt Quelle für interne Ticketrechte und Auditdaten.
- GitHub bleibt Quelle für Issue-/PR-spezifische Inhalte.
- Status-/Prioritätsmapping wird pro Verbindung konfiguriert.
- Kommentare werden nicht automatisch gespiegelt, solange keine klare
  Herkunftsmarkierung und Duplikat-ID vorhanden ist.
- Konflikte werden als `sync_state=error` sichtbar gemacht, nicht still
  überschrieben.

Für eingehende Änderungen wird bevorzugt GitHub `projects_v2_item`-Webhook mit
HMAC-Validierung eingesetzt; Polling bleibt Fallback. Schreibaufträge laufen
über eine idempotente Outbox mit externer Event-ID.

## Datenfluss MVP

1. Benutzer legt im HydraHive-Projekt eine GitHub-Verbindung an.
2. Backend liest Credential-Referenz aus dem Credential-Store.
3. Provider fragt ausschließlich die GitHub-GraphQL-API ab.
4. Response wird auf ein internes, tokenfreies DTO reduziert.
5. Ticket-Link und Sync-Status werden lokal gespeichert.
6. Agenten erhalten nur die für ihren Kontext erlaubten Read-/Link-Tools.

## Sicherheit

- Credential-Werte nie in Datenbank, Audit-Payload, Frontend oder Tool-Result
- GitHub-Host fest verdrahtet/allowlisted; keine SSRF über konfigurierte URL
- GraphQL-Variablen parametrisiert, keine String-Interpolation von User-Input
- Owner, Repository, Issue-Nummer und Project-ID validieren
- Rate-Limit- und Upstream-Fehler als stabile interne Fehlercodes abbilden
- Response-Größe und Seitenzahlen begrenzen
- Logs nur mit Connection-ID/Owner/Repo, niemals Token oder Authorization-Header
- Schreib-Sync standardmäßig deaktiviert

## Implementierungsreihenfolge

### Task 1 — Schema und Verbindung

- [ ] Migration für Connections und Ticket-Links
- [ ] Pydantic-Modelle und Credential-Referenzvalidierung
- [ ] Tests für Eindeutigkeit, User-/Projektisolation und Secret-Redaction

### Task 2 — Provider und Read-only-API

- [ ] GitHub-GraphQL-Client mit festem Endpoint und Timeout
- [ ] Project-/Item-/Issue-DTOs
- [ ] API-Routen inklusive Connection-Check
- [ ] Mock-Tests für Erfolg, Auth-Fehler, Rate-Limit, Pagination und Upstream-Fehler

### Task 3 — Ticket-Verknüpfung und Agenten-Tools

- [ ] Link/Unlink-Route und Audit-Events
- [ ] Read-/Link-Tools mit bestehendem Ticket-Rechtemodell
- [ ] Tool-Manifest/Skill-Zuordnung mit Least Privilege

### Task 4 — Frontend-MVP

- [ ] Projekt-Integrationseinstellungen
- [ ] GitHub-Statuskarte im Ticketdetail
- [ ] Project-Items-Ansicht und Link-Dialog
- [ ] i18n, Loading-, Fehler- und Permission-Zustände

### Task 5 — Push und Sync (separater Plan)

- [ ] explizite Schreibbestätigung
- [ ] Outbox/Idempotenz
- [ ] Webhook-Verifikation
- [ ] Konflikt- und Mapping-Regeln

## Akzeptanzkriterien für den MVP

- [ ] Ein HydraHive-Projekt kann eine GitHub-Verbindung ohne Token-Leak speichern.
- [ ] Projects, Items und Issues können read-only geladen werden.
- [ ] Ein bestehendes GitHub-Issue kann mit einem HydraHive-Ticket verknüpft werden.
- [ ] Ticket- und Agentenberechtigungen werden bei jedem Zugriff geprüft.
- [ ] Ein Agent ohne GitHub-Tool-Freigabe sieht keine GitHub-Tools.
- [ ] GitHub-Ausfälle blockieren lokale Ticketfunktionen nicht.
- [ ] Bestehende Ticket- und Task-Tests bleiben grün.
