# HydraHive Tickets — Spezifikation V1

## Ziel

HydraHive erhält ein natives, internes Team-Ticketsystem. Tickets, Kommentare,
Zuständigkeiten und Historie werden im Modul selbst gespeichert und sind über eine
HydraHive-Weboberfläche sowie eine stabile Agenten-Tool/API-Schicht nutzbar.

V1 ist ausschließlich für interne HydraHive-Benutzer, Teams und Agenten bestimmt.
Es gibt keine externen Kunden, keine öffentliche Ticketansicht und keine
E-Mail-Ingestion oder E-Mail-Antwort.

## Begriffe

- **Ticket:** Interner Vorgang mit Titel, Beschreibung, Status, Priorität,
  Zuständigkeit und Verlauf.
- **Kommentar:** Interne Nachricht im Ticketverlauf. Alle Kommentare sind intern;
  eine Public/Private-Unterscheidung entfällt in V1.
- **Team:** HydraHive-interne Arbeitsgruppe mit Mitgliedern und optionalen Leads.
- **Task:** Konkrete Arbeit, die aus einem Ticket entstehen kann. Ein Ticket kann
  optional mit einem bestehenden Task, Projekt oder einer Session verknüpft werden.
- **Agentenaktion:** Von einem HydraHive-Agenten im Benutzer-/Projektkontext
  ausgeführte, auditierbare Ticketoperation.

## Status und Prioritäten

Statuswerte:

- `open` — neu angelegt, noch nicht triagiert
- `triaged` — bewertet und einer Zuständigkeit zugeordnet oder zur Bearbeitung bereit
- `in_progress` — aktiv in Bearbeitung
- `waiting` — wartet auf interne Informationen oder eine Entscheidung
- `resolved` — Lösung vorhanden, Abschluss steht noch aus
- `closed` — abgeschlossen
- `cancelled` — bewusst abgebrochen

Erlaubte Übergänge:

- `open` → `triaged`, `in_progress`, `cancelled`
- `triaged` → `in_progress`, `waiting`, `cancelled`
- `in_progress` → `waiting`, `resolved`, `cancelled`
- `waiting` → `in_progress`, `resolved`, `cancelled`
- `resolved` → `closed`, `in_progress`
- `closed` → `open`
- `cancelled` → `open`

Prioritäten:

- `low`
- `normal`
- `high`
- `urgent`

## Sichtbarkeit und Berechtigungen

V1 enthält ausschließlich interne Inhalte. Alle authentifizierten HydraHive-Benutzer
können interne Tickets lesen und kommentieren. Zusätzlich gelten folgende
Workflow-Rechte:

- Ein Benutzer darf Tickets erstellen und eigene Tickets bearbeiten.
- Ein direkt zugewiesener Benutzer darf Status und Bearbeitungsfelder ändern.
- Teammitglieder dürfen Tickets ihres Teams bearbeiten.
- Team-Leads dürfen Teammitglieder und Teamzuweisungen verwalten.
- System-Admins dürfen alle Tickets, Teams, Zuweisungen und Auditdaten verwalten.
- Agenten erben im Tool-Kontext die Rechte des aufrufenden Benutzers; ein Agent
  bekommt keine zusätzlichen globalen Rechte.
- Löschen ist in V1 nicht vorgesehen. Falsche oder erledigte Tickets werden
  geschlossen bzw. abgebrochen, damit die Historie erhalten bleibt.

Projekt-, Task- und Session-IDs sind optionale Verknüpfungen. Das Modul prüft beim
Setzen nur die Form und protokolliert die Referenz; die jeweilige Zielressource
bleibt für ihr eigenes Modul bzw. den Core zuständig.

## Datenmodell

Die Tabellen liegen im Modulpräfix `module_tickets_` und werden additiv über
`migrations/001_tickets.sql` angelegt.

### `module_tickets`

- `id` — UUID, Primärschlüssel
- `number` — fortlaufende interne Ticketnummer, eindeutig
- `title` — 1–200 Zeichen
- `description` — optionaler Text
- `status` — erlaubter Statuswert
- `priority` — erlaubter Prioritätswert
- `category` — optional, maximal 80 Zeichen
- `created_by` — HydraHive-User-ID
- `assigned_to` — optionale User-ID
- `team_id` — optionale Team-ID
- `project_id` — optionale Projekt-ID
- `task_id` — optionale Task-ID
- `session_id` — optionale Session-ID
- `created_at`, `updated_at`
- `resolved_at`, `closed_at` — optionaler Zeitstempel

### `module_ticket_comments`

- `id` — UUID
- `ticket_id` — Ticketreferenz
- `author_id` — User- oder Agent-Identität aus dem Tool-Kontext
- `author_kind` — `user` oder `agent`
- `body` — 1–20.000 Zeichen
- `created_at`

Kommentare sind nach Veröffentlichung unveränderlich. Korrekturen erfolgen als
neuer Kommentar; Löschung ist nur als Admin-Reparatur außerhalb des normalen V1-
Workflows vorgesehen.

### `module_ticket_teams`

- `id` — UUID
- `name` — eindeutig, 1–100 Zeichen
- `description` — optional
- `created_by`, `created_at`, `updated_at`

### `module_ticket_team_members`

- `team_id`
- `user_id`
- `role` — `member` oder `lead`
- `created_at`
- eindeutiger zusammengesetzter Schlüssel aus Team und Benutzer

### `module_ticket_events`

Append-only Audit-Historie:

- `id`
- `ticket_id`
- `actor_id`
- `actor_kind`
- `event_type`
- `payload_json` — nur strukturierte, nicht geheime Änderungsdaten
- `created_at`

### `module_ticket_notifications`

Interne, zunächst polling-basierte Benachrichtigungen:

- `id`
- `user_id`
- `ticket_id`
- `kind`
- `read_at`
- `created_at`

### Anhänge

V1 unterstützt optionale interne Anhänge zu Tickets und Kommentaren. Die Datei
liegt außerhalb der Datenbank im vom Modul verwalteten Datenspeicher; die Datenbank
enthält nur Metadaten:

- UUID und Ticket-/Kommentarreferenz
- Originalname, MIME-Typ und Dateigröße
- zufälliger Storage-Key
- SHA-256-Prüfsumme
- Uploader und Zeitstempel

Maximale Dateigröße in V1: 25 MiB. Pfade werden nie aus dem Originalnamen gebildet.

## API

Prefix: `/api/modules/tickets`

V1-Routen:

- `GET /tickets` — paginierte Liste mit Filtern für Status, Priorität, Team,
  Zuständigkeit, Projekt und Suchtext
- `POST /tickets` — Ticket erstellen
- `GET /tickets/{ticket_id}` — Ticketdetail inklusive aktueller Zusammenfassung
- `PATCH /tickets/{ticket_id}` — erlaubte Metadaten ändern
- `GET /tickets/{ticket_id}/comments` — Verlauf mit Cursor/Pagination
- `POST /tickets/{ticket_id}/comments` — internen Kommentar hinzufügen
- `POST /tickets/{ticket_id}/attachments` — Anhang hochladen
- `GET /tickets/{ticket_id}/attachments/{attachment_id}` — eigenen Anhang laden
- `GET /teams` — Teams auflisten
- `POST /teams` — Team anlegen, nur Admin
- `PATCH /teams/{team_id}` — Team ändern, Admin oder Team-Lead
- `POST /teams/{team_id}/members` — Mitglied hinzufügen/Lead setzen
- `DELETE /teams/{team_id}/members/{user_id}` — Mitglied entfernen
- `GET /notifications` — ungelesene/aktuelle Ticketbenachrichtigungen
- `POST /notifications/{notification_id}/read` — Benachrichtigung quittieren

Alle Routen verlangen HydraHive-Authentifizierung. Request-Bodies werden mit
Pydantic validiert; Eingaben werden niemals als SQL oder Dateipfad zusammengesetzt.

## Agenten-Tools

Die Agenten verwenden nicht direkt SQL oder interne Modulrouten, sondern diese
stabile Tool-Schicht:

- `ticket_list` — Tickets suchen/filtern
- `ticket_read` — Ticket und Verlauf lesen
- `ticket_create` — internes Ticket erstellen
- `ticket_comment` — internen Kommentar hinzufügen
- `ticket_update` — Status, Priorität, Team, Zuständigkeit und Verknüpfungen ändern
- `ticket_create_task` — optional einen verknüpften HydraHive-Task anlegen

Jede Tool-Aktion verwendet `ToolContext.user_id`, `agent_id`, `session_id` und
`project_id`, prüft die Rechte erneut und schreibt ein Audit-Event. Tool-Ergebnisse
liefern kompakte Metadaten statt vollständiger Anhänge.

## Frontend

Das Modul registriert eine Route `/tickets` und eine Navigation im Bereich
`working`. Die V1-Oberfläche besteht aus:

- Ticket-Inbox mit Suche, Filtern und Status-/Prioritätsbadges
- Ticketdetail mit Metadaten, Zuständigkeit, Team und Verknüpfungen
- chronologischem internen Verlauf
- Formular für Ticket und Kommentar
- Team-/Zuweisungs-Auswahl entsprechend den Benutzerrechten
- Anhang-Upload und Download
- ungelesenen Ticketbenachrichtigungen

Die Oberfläche nutzt dieselben API-Verträge wie die Agenten-Tools. Deutsch und
Englisch werden von Anfang an als i18n-Schlüssel angelegt.

## Benachrichtigungen

V1 verwendet keine E-Mail und keine externen Push-Dienste. Benachrichtigungen
werden bei Erstellung, Zuweisung, Teamwechsel, Kommentar, Eskalation und Status-
änderung als interne Datensätze angelegt. Die UI fragt diese zunächst periodisch
ab. Echtzeit-SSE/WebSocket ist nicht Bestandteil von V1.

## Datenschutz und Sicherheit

- ausschließlich interne, authentifizierte HydraHive-Benutzer
- keine öffentliche Ticket-/Kommentaransicht
- keine E-Mail-Anbindung in V1
- Anhänge mit UUID-Storage-Key und Größenlimit
- keine Geheimnisse in Audit-Payloads oder Agentenergebnissen
- Kommentare unveränderlich, Audit append-only
- keine Löschroute im normalen UI
- keine direkten Dateisystempfade im Frontend
- Agentenrechte werden serverseitig erneut geprüft

## Nicht Bestandteil von V1

- externe Kundenportale
- E-Mail-Piping und E-Mail-Antworten
- SLA-Zeitberechnung und externe Eskalationskanäle
- öffentliche Kommentare
- Volltextsuche über Anhänge
- automatische KI-Klassifizierung ohne expliziten Agentenaufruf
- osTicket-Synchronisation
- Echtzeit-SSE/WebSocket
