# HydraHive Tickets V4 — GitHub Hybrid Workbench

## Ziel

GitHub-Issues sollen im Tickets-Modul nicht mehr als kleine externe Liste erscheinen,
sondern als vollwertige, zentral bedienbare Tickets. HydraHive übernimmt interne
Workflow-Daten; GitHub bleibt Quelle für Issue-/Project-Daten. Änderungen werden
explizit und nachvollziehbar synchronisiert.

## Quellen und Besitz

**GitHub ist führend für:** Issue-Titel, Beschreibung, Open/Closed-State, Labels,
GitHub-Assignee, Issue-Nummer/URL und Project-Item-Status.

**HydraHive ist führend für:** internes Ticket, Priorität, Team, SLA/Fälligkeit,
interne Zuständigkeit, interne Kommentare, Anhänge, Audit und Agenten-/Task-Kontext.

Konflikte werden nicht still überschrieben. Sie werden mit Sync-Status und letzter
Fehlermeldung angezeigt und benötigen eine explizite Aktion.

## UI

Die aktuelle Sidebar-Liste wird durch eine zentrale GitHub-Workbench ersetzt:

- Verbindung / Repository / GitHub-Project oben
- Tabs: `Tickets`, `Project-Board`, `Sync & Aktionen`
- mittlere Liste mit GitHub-Tickets und HydraHive-Feldern
- Detailansicht nutzt die vorhandene Ticketdetail-Ansicht
- externe URL, Sync-Status, letzter Sync und Konfliktstatus sichtbar
- Suche, Status-, Label-, Assignee- und Project-Filter

Ein Issue wird beim Import anhand von `connection_id + owner + repository + issue_number`
eindeutig wiedererkannt. Wiederholter Sync erzeugt kein Duplikat.

## Aktionen

### Read/Import

- offene und geschlossene Issues des verbundenen Repositories laden
- ausgewählte Issues als HydraHive-Tickets importieren
- alle passenden Issues synchronisieren
- bestehende lokale Links aktualisieren
- Project-Items und Project-Felder lesen

### GitHub-Push (nur bei explizit aktiviertem Schreibmodus)

- Issue-Titel und Beschreibung ändern
- Issue öffnen/schließen
- Labels setzen/entfernen
- GitHub-Assignee ändern
- neues Issue aus HydraHive anlegen
- Issue in Project aufnehmen/entfernen
- Project-Status und unterstützte Single-Select-Felder ändern

Jede Schreibaktion wird als einzelne, idempotente Operation ausgeführt und als
Audit-Event gespeichert. Fehler lassen das lokale Ticket bestehen und setzen den
Sync-Status auf `error`.

## Berechtigungen und Sicherheit

- Verbindung bleibt standardmäßig `read_only`.
- Schreibzugriff wird pro Verbindung explizit auf `push` oder `bidirectional` gesetzt.
- Jede Route prüft HydraHive-Projektzugriff und Verbindung.
- GitHub-Token bleibt ausschließlich in der Projektkonfiguration.
- GitHub-Endpoint ist fest auf `https://api.github.com/graphql` begrenzt.
- Keine externen URLs aus Benutzerinput werden serverseitig gefetcht.
- Upstream-Fehler werden als stabile, tokenfreie Fehlercodes gemeldet.

## Datenmodell

Die bestehende `module_ticket_github_links`-Tabelle bleibt die eindeutige Zuordnung
zwischen lokalem Ticket und externem Issue. Ergänzt werden Sync-Metadaten für den
letzten GitHub-Snapshot und Project-Item-Felder, ohne Tokenwerte zu speichern.

## Nichtziele der ersten Hybrid-Lieferung

- vollständige Kopie jeder GitHub-Projects-Sonderfunktion
- automatische bidirektionale Webhook-Synchronisation ohne sichtbaren Status
- automatische Kommentare-Spiegelung ohne Herkunfts-/Duplikat-ID
- Änderungen an GitHub bei bestehender `read_only`-Verbindung
- beliebige GitHub-Organisationen ohne Tokenberechtigung

## Akzeptanzkriterien

- [ ] GitHub-Issues erscheinen in einer zentralen Ticketansicht, nicht nur in der Sidebar.
- [ ] Ein Issue kann idempotent als HydraHive-Ticket importiert werden.
- [ ] Importierte Tickets sind mit bestehender Ticketansicht, Kommentaren, SLA, Team und Priorität bedienbar.
- [ ] Titel/Beschreibung/State/Labels/Assignee werden nachvollziehbar synchronisiert.
- [ ] Project-Items und Statusfelder können gelesen und bei aktivem Schreibmodus geändert werden.
- [ ] Read-only-Verbindungen bleiben unverändert schreibgeschützt.
- [ ] Alle Schreibfehler bleiben sichtbar und erzeugen keine stillen lokalen Datenverluste.
- [ ] Tokens erscheinen weder in DB, API-Response, Frontend, Audit-Event noch Fehlertext.
- [ ] Bestehende Ticket- und GitHub-Tests bleiben grün.
