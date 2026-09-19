# HydraHive Tickets V2.1 — Operations, SLA und gespeicherte Ansichten

## Ziel

V2.1 erweitert das interne Ticketsystem um berechnete Fälligkeiten, editierbare
SLA-Ausnahmen, operative Übersichten und sichere Massenänderungen. Die V1-API,
Agentenrechte und der interne Charakter des Moduls bleiben erhalten.

## Fälligkeiten und SLA

Jedes Ticket erhält eine effektive Fälligkeit (`due_at`). Sie wird standardmäßig
automatisch aus dem aktiven SLA-Profil, der Priorität und dem relevanten
Startzeitpunkt berechnet:

- `response_due_at` — Frist für die erste interne Antwort
- `resolution_due_at` — Frist bis zur Lösung
- `due_at` — aktuell wirksame Lösungsfrist für Sortierung und Überfälligkeitslogik
- `due_at_source` — `sla`, `manual` oder `none`
- `first_response_at` — Zeitpunkt des ersten Kommentars eines anderen Akteurs

Eine manuelle Bearbeitung überschreibt die berechnete Fälligkeit für dieses Ticket.
Die UI muss dabei klar anzeigen, dass eine Ausnahme aktiv ist. Beim Zurücksetzen
der manuellen Fälligkeit fällt das Ticket wieder auf die SLA-Berechnung zurück.

Die Standardberechnung verwendet Kalenderzeit und keine Arbeitszeitkalender. Das
vermeidet in V2.1 eine versteckte Zeitzonen-/Feiertagslogik. Ein späteres V2.x kann
Arbeitszeiten ergänzen.

### Standard-SLA-Profil

Das Modul legt ein editierbares Standardprofil an. Die initialen Werte sind:

| Priorität | Erste Antwort | Lösung |
|---|---:|---:|
| `urgent` | 4 Stunden | 24 Stunden |
| `high` | 8 Stunden | 72 Stunden |
| `normal` | 24 Stunden | 120 Stunden |
| `low` | 72 Stunden | 240 Stunden |

SLA-Profile werden von Admins verwaltet. Änderungen an einem Profil verändern nur
neu berechnete oder noch nicht manuell überschriebene Tickets; bereits protokollierte
Zeitpunkte und manuelle Ausnahmen werden nicht rückwirkend verfälscht.

## Dashboard

Das Operations-Dashboard liefert über einen einzelnen API-Aufruf:

- Gesamtzahl offener Tickets
- Anzahl je Status und Priorität
- nicht zugewiesene Tickets
- eigene Tickets
- Team-Tickets
- überfällige Tickets
- Tickets mit baldiger Fälligkeit
- durchschnittliche Zeit bis zur ersten Antwort
- durchschnittliche Lösungszeit

Die Kennzahlen respektieren die Sichtbarkeit des aufrufenden Benutzers. Es werden
keine Ticketdaten aus Teams oder Bereichen zurückgegeben, auf die der Benutzer
keinen Zugriff hat.

## Gespeicherte Ansichten

Benutzer können Filter und Sortierung als persönliche Ansicht speichern. Admins und
Team-Leads können zusätzlich eine Teamansicht anlegen, die Teammitgliedern angezeigt
wird.

Gespeichert werden nur deklarative Filter:

- Status, Priorität, Team, Zuständigkeit, Projekt
- Suchtext
- `overdue` und `unassigned`
- Sortierfeld und Sortierrichtung

Keine freien SQL-Ausdrücke oder unvalidierte Query-Fragmente werden gespeichert.

## Bulk-Aktionen

Erlaubte V2.1-Massenänderungen:

- Status setzen
- Priorität setzen
- Team setzen/entfernen
- Benutzer zuweisen/entfernen
- Fälligkeit manuell setzen oder SLA-Berechnung wiederherstellen

Jedes Ticket wird einzeln gegen die bestehenden V1-Berechtigungen geprüft. Eine
Bulk-Aktion darf bei einem einzelnen unberechtigten Ticket nicht stillschweigend
durchgeführt werden: Die Antwort enthält pro Ticket `updated`, `skipped` oder `error`.
Jede tatsächliche Änderung erzeugt ein eigenes Audit-Event und eine Benachrichtigung.

## Erinnerungen und Eskalationen

V2.1 bleibt beim vorhandenen internen Notification-Polling. Es gibt keine E-Mail,
keinen externen Push-Dienst und kein SSE/WebSocket.

Benachrichtigungen werden höchstens einmal pro Ticket und Eskalationsstufe erzeugt:

- `due_soon` — innerhalb des konfigurierten Vorwarnfensters
- `overdue` — Fälligkeit überschritten
- `sla_response_breached` — erste Antwortfrist überschritten
- `sla_resolution_breached` — Lösungsfrist überschritten

Die Berechnung wird bei Dashboard-/Listenabfragen und über einen idempotenten
Service-Aufruf ausgeführt. Ein Hintergrunddienst ist für V2.1 nicht erforderlich.

## API

Neue Routen unter `/api/modules/tickets`:

- `GET /dashboard`
- `GET /saved-views`
- `POST /saved-views`
- `PATCH /saved-views/{view_id}`
- `DELETE /saved-views/{view_id}`
- `POST /bulk-update`
- `GET /sla/profiles`
- `POST /sla/profiles`
- `PATCH /sla/profiles/{profile_id}`

Bestehende `GET /tickets`-Filter werden um `overdue`, `due_before` und
`sort`/`direction` erweitert. Bestehende Clients ohne diese Parameter bleiben
kompatibel.

## Frontend

- Dashboard-Karte oberhalb der Ticket-Inbox
- Fälligkeitsindikator in Liste und Detailansicht
- manueller Fälligkeitseditor mit „SLA-Berechnung wiederherstellen"
- Ansichtsauswahl und Ansicht speichern
- Mehrfachauswahl in der Inbox mit Bestätigungsdialog
- Ergebnisdarstellung für teilweise erfolgreiche Bulk-Aktionen
- Admin-/Lead-Dialog für SLA-Profile
- vorhandene i18n-Schlüssel für Deutsch und Englisch erweitern

## Akzeptanzkriterien

- [ ] Ein neues Ticket erhält abhängig von der Priorität automatisch SLA-Fristen.
- [ ] Eine manuelle Fälligkeit überschreibt die Berechnung und ist rücksetzbar.
- [ ] SLA-Fristen und Überfälligkeit werden im Dashboard, in der Liste und im Detail angezeigt.
- [ ] Dashboard-Kennzahlen beachten die Benutzer- und Teamrechte.
- [ ] Persönliche und berechtigte Teamansichten können gespeichert, geändert und gelöscht werden.
- [ ] Bulk-Aktionen prüfen jedes Ticket einzeln und auditieren jede Änderung.
- [ ] Erinnerungen werden idempotent und nur einmal je Eskalationsstufe erzeugt.
- [ ] V1-Routen, Agenten-Tools und V1-Tests bleiben kompatibel.
- [ ] Die Modul-Tests und der Frontend-Produktionsbuild bleiben grün.

## Nicht in V2.1

- Arbeitszeitkalender, Feiertage und Zeitzonenregeln pro Team
- E-Mail, Slack, Matrix oder externe Push-Benachrichtigungen
- automatische KI-Klassifizierung ohne explizite Aktion
- GitHub-/Gitea-Synchronisation
- öffentliche Kundenportale
- Echtzeit-SSE/WebSocket
