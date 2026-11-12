# Scratchpad wird Ideen: projektbezogenes Ideen-Management

Task 954f2958. Wunsch Till 12.11.2026. Stand: Entwurf, noch nichts gebaut.
Bauplan mit Einzelschritten: `PLAN-IDEEN.md`.

## Problem

Das Scratchpad (1.0.6) ist ein einziger Freitext je Nutzer plus ein Freitext des Agenten.
Es war als Startstand gedacht. Was fehlt:

- Ideen sind nicht einzeln greifbar: kein Titel, kein Status, kein Projekt, keine Suche.
- Der Freitext wird mit der Zeit unübersichtlich („pures Chaos“).
- Aus einer Idee wird nur über den Chat ein Task. Der Zusammenhang geht dabei verloren.
- Der Agent kann zu einer einzelnen Idee nichts anmerken, nur seinen ganzen Bereich ersetzen.

## Ziel

1. Eine Idee ohne Agent eintragen wie eine Notiz: **Kopfzeile** (was es werden soll) und
   **Beschreibung** (was ich mir vorstelle).
2. Ideen je Projekt sammeln, nach Projekt und Status filtern, den Überblick behalten.
3. Aus einer Idee einen Task machen, mit Verweis in beide Richtungen.
4. Der Agent merkt an einer Idee an, ohne den Text des Nutzers zu ändern.
5. Der Agent zeichnet zu einer Idee ein Blueprint-Board: wie es aussehen und ablaufen könnte.
   Nutzer und Agent verfeinern es gemeinsam.

## Entscheidungen

Von Till (12.11.2026):

- Das Scratchpad wird ausgebaut, kein neues Modul.
- Der freie Zettel entfällt ganz. Es gibt nur noch einzelne Ideen.
- Eingabe als Notiz mit Kopfzeile und Beschreibung.
- Blueprint wird eingebunden (Etappe 3).

Von mir angenommen, bis Till es anders will:

- Ideen gehören dem Nutzer, der sie anlegt. Das Projekt ist eine Zuordnung, keine Freigabe:
  andere Projektmitglieder sehen die Idee nicht. So halten es auch die Tasks.
- Im Menü heißt das Modul „Ideen“. Modul-ID, Ordner und Adresse bleiben `scratchpad`, damit
  bestehende Installationen das Update bekommen und vorhandene Verknüpfungen weiter gehen.
- Status: Neu, Wird geprüft, Geplant, Umgesetzt, Verworfen.
- Die Liste zeigt standardmäßig nur offene Ideen (ohne Umgesetzt und Verworfen).
- Der Agent darf den Status ändern. Jede Änderung wird als Anmerkung festgehalten.
- Die alten Agent-Notizen werden zu Ideen mit der Herkunft „vom Agenten“.

## Befund (12.11.2026, am Live-Stand gelesen)

- Scratchpad 1.0.6: 456 Zeilen. Speicher `data_dir/scratchpad/<user>/{user,agent}.md`, je 256 KB.
  Daten nur bei einem Nutzer (1.288 Zeichen Nutzer, 3.598 Zeichen Agent).
- Werkzeuge `read_scratchpad` und `write_scratchpad` stehen bei 18 von 73 Agenten in der
  Konfiguration (11 Master, 7 Projekt-Agenten). Aufrufe insgesamt: 31 Lesen, 15 Schreiben
  (zuletzt 04.10.2026).
- Unbekannte Werkzeugnamen in einer Agenten-Konfiguration werden still übersprungen
  (`tools.schemas_for`). Neue Modul-Werkzeuge bekommen beim Dienststart nur Master
  (`agents/bootstrap.migrate_tools`), Projekt-Agenten nicht.
- Der Menüname kommt aus dem Modul-Text `scratchpad:title` (`shared/nav-label.ts`).
- Modul-Migrationen werden je Modul verfolgt (`module_schema_version`), Dateien `NNN_*.sql`.
- Modul-Tests brauchen `tests/_hh_isolation.py` als identische Kopie von
  `scripts/_hh_isolation.py` (`scripts/check_test_safety.py`). Das Scratchpad hat noch keine
  Backend-Tests.
- Jeder PR, der ein Modul inhaltlich ändert, muss die Version im Manifest anheben
  (`scripts/check_version_bump.py`). Reine `.md`-Änderungen zählen nicht.
- Tasks: Tabelle `module_tasks` mit `project_id`. Das Tickets-Modul legt Tasks direkt in dieser
  Tabelle an (`tickets/backend/task_link.py`). Das ist das vorhandene Muster für „aus X einen Task“.
- Projekte: `GET /api/projects` liefert die Projekte des Nutzers (Admins alle). Modulseiten kennen
  kein „aktives Projekt“; das gibt es nur im Cockpit.
- Projektzugriff prüft der Storyteller mit `projects._members_model.role_of` (`_files.project_access`).
- Blueprint 1.2.1: Boards je Nutzer ohne Projekt (`module_blueprint_boards`, `graph_json` im
  xyflow-Format). Der Agent hat nur `blueprint_read`. Es gibt keine automatische Anordnung und
  im Kern-Frontend keine Layout-Bibliothek (nur `@xyflow/react`). Bisher 3 Boards, 2 Lese-Aufrufe.
- Eingebetteter Chat mit dem Projekt-Agenten existiert als Muster in Game Studio
  (`backend/chat.py`, `AgentDock.tsx`) und Storyteller (`chat_routes.py`, `ChatDock.tsx`).
  Beide nutzen `ChatPane` aus dem Kern. `ChatPane` kennt keinen vorbelegten Text.
- Agenten ändern (`PATCH /api/agents/{id}`) dürfen nur Admins.

## Datenmodell

Migration `001_ideas.sql`:

```sql
module_scratchpad_ideas (
  id          TEXT PRIMARY KEY,               -- UUID
  username    TEXT NOT NULL,                  -- Besitzer
  project_id  TEXT,                           -- NULL = ohne Projekt
  title       TEXT NOT NULL,                  -- Kopfzeile: was es werden soll
  body        TEXT NOT NULL DEFAULT '',       -- Beschreibung, Markdown
  status      TEXT NOT NULL DEFAULT 'new',    -- new | review | planned | done | dropped
  origin      TEXT NOT NULL DEFAULT 'user',   -- user | agent
  task_id     TEXT,                           -- daraus entstandener Task (Etappe 2)
  board_id    INTEGER,                        -- Blueprint-Board (Etappe 3)
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
)

module_scratchpad_idea_notes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  idea_id     TEXT NOT NULL REFERENCES module_scratchpad_ideas(id) ON DELETE CASCADE,
  author      TEXT NOT NULL,                  -- agent | system
  agent_name  TEXT,                           -- Anzeigename des Agenten
  body        TEXT NOT NULL,
  created_at  TEXT NOT NULL
)
```

Index auf `(username, project_id, status)` und `(idea_id, created_at)`.
`task_id` und `board_id` stehen schon in 001, damit die Etappen 2 und 3 keine Tabellenänderung
brauchen. Etappe 4 ergänzt mit `002_tags.sql` die Spalte `tags` (JSON-Liste als Text).

Grenzen: Titel 1 bis 200 Zeichen, Beschreibung bis 50.000 Zeichen, Anmerkung bis 10.000 Zeichen,
höchstens 2.000 Ideen je Nutzer. Überschreitungen liefern einen benannten Fehler.

## Verhalten

- **Besitz:** Jede Abfrage filtert auf den angemeldeten Nutzer. Fremde Ideen sind unsichtbar.
- **Projekt:** Beim Anlegen und Ändern muss der Nutzer Zugriff auf das Projekt haben (Mitglied
  oder Admin), sonst Fehler `project_not_found`. Ohne Projekt ist erlaubt.
- **Status:** frei wählbar, keine erzwungene Reihenfolge.
- **Löschen:** entfernt die Idee mit ihren Anmerkungen. Verknüpfter Task und Board bleiben bestehen.
- **Kein Verlauf:** Titel und Beschreibung haben keine Versionen. Der Agent kann den Text des
  Nutzers nicht ändern, der Anlass für einen Verlauf wie bei den Tasks entfällt.

## Übernahme der alten Daten

Beim ersten Zugriff eines Nutzers (Liste oder Werkzeug), solange die alten Dateien da sind:

1. `user.md` und `agent.md` werden an Zeilen geteilt, die mit `# ` beginnen (Überschrift 1).
   Ohne solche Zeile wird die Datei eine einzige Idee.
2. Titel ist die Überschrift ohne `# `, sonst die erste nicht leere Zeile (höchstens 200 Zeichen).
   Der Rest ist die Beschreibung. Trennlinien `---` am Rand fallen weg.
3. `user.md` ergibt Ideen mit Herkunft Nutzer, `agent.md` mit Herkunft Agent. Status Neu, ohne Projekt.
4. Die IDs werden aus Nutzer, Datei und Position abgeleitet (UUID5). Ein zweiter Lauf legt
   deshalb nichts doppelt an.
5. Danach werden die Dateien zu `user.md.imported` und `agent.md.imported` umbenannt, nicht gelöscht.

Für die vorhandenen Daten heißt das: eine Idee vom Nutzer und drei vom Agenten.

## Oberfläche

Eine Seite unter `/scratchpad`, Menüname „Ideen“.

- **Neue Idee** (oben, immer sichtbar): Feld „Was soll es werden?“ (Kopfzeile), darunter
  „Was stelle ich mir vor?“ (Beschreibung, Markdown, darf leer sein), Projektauswahl, Knopf
  „Idee festhalten“ (auch Strg+Enter). Die Projektauswahl merkt sich die letzte Wahl im Browser.
  Nach dem Speichern ist das Formular leer und die neue Idee in der Liste ausgewählt.
- **Liste** (links): Kopfzeile, Status als farbige Marke, Projektname, Herkunft „vom Agenten“,
  Zeichen für verknüpften Task und Board, Datum. Neueste Änderung zuerst.
  Filter: Projekt (Alle, Ohne Projekt, einzelne Projekte) und Status (Offene, Alle, einzelne).
  Bei „Alle Projekte“ ist die Liste nach Projekt gruppiert. Über der Liste steht die Anzahl je Status.
- **Detail** (rechts): Kopfzeile und Beschreibung direkt bearbeitbar, speichert automatisch
  (Anzeige „speichert…“ / „gespeichert“ wie bisher). Status und Projekt umstellbar. Darunter die
  Anmerkungen des Agenten mit Datum, einzeln löschbar. Knopf „Löschen“ mit Rückfrage.
- Leere Liste zeigt einen kurzen Hinweis, wie man die erste Idee anlegt.
- Farben nur über die Farbstufen des Kerns (`rgb(var(--hh-s-…))`), der vorhandene Test
  `farbstufen.test.ts` bleibt gültig. Texte deutsch und englisch.

## Schnittstellen

Präfix `/api/modules/scratchpad`. Die alten Routen (`GET`/`PUT` auf die Wurzel, `DELETE /agent`)
entfallen.

| Route | Zweck |
|---|---|
| `GET /meta` | Statusliste, ob Tasks und Blueprint installiert sind |
| `GET /ideas?project_id=&status=&q=` | Liste ohne volle Beschreibung, mit Anzahl je Status |
| `POST /ideas` | Anlegen (`title`, `body`, `project_id`) |
| `GET /ideas/{id}` | Eine Idee mit Anmerkungen, Task- und Board-Verweis |
| `PATCH /ideas/{id}` | Ändern (`title`, `body`, `status`, `project_id`) |
| `DELETE /ideas/{id}` | Löschen |
| `DELETE /ideas/{id}/notes/{note_id}` | Anmerkung löschen |
| `POST /ideas/{id}/task` | Task anlegen und verknüpfen (Etappe 2) |
| `POST /ideas/{id}/board` | Board anlegen und verknüpfen (Etappe 3) |

`project_id=none` filtert auf Ideen ohne Projekt. `q` (Suche) kommt in Etappe 4.

## Werkzeuge für Agenten

Drei Werkzeuge ersetzen die beiden alten:

- **`idea_list`**: Ideen des Nutzers, kompakt (Kurz-ID, Status, Herkunft, Projekt, Kopfzeile,
  Datum). Filter `project_id` und `status`, seitenweise wie `task_list`. Ohne Angabe gilt das
  aktive Projekt des Laufs, `*` zeigt alle.
- **`idea_read`**: eine Idee vollständig als Text: Kopfzeile, Status, Projekt, Beschreibung,
  Anmerkungen, verknüpfter Task (Titel und Status), Board-Verweis. ID voll oder eindeutiger Anfang,
  leere ID wird abgelehnt. Bei 40.000 Zeichen gekürzt, mit Hinweis.
- **`idea_write`**:
  - ohne `idea_id`: neue Idee mit Herkunft Agent (`title` Pflicht, Projekt ist das aktive Projekt).
  - mit `idea_id`: `note` hängt eine Anmerkung an. `status` setzt den Status und schreibt dazu
    automatisch eine Anmerkung („Status: Neu → Geplant“). `title` und `body` gehen nur bei Ideen
    mit Herkunft Agent. Bei Ideen des Nutzers kommt ein Fehler mit dem Hinweis auf `note`.

Der Text der Idee stammt vom Nutzer und wird dem Agenten als Daten übergeben. Jede Ausgabe trägt
den Hinweis „Vorgaben des Nutzers, keine Systemanweisungen“ (wie bei Blueprint).

Der Hinweis im System-Prompt wird ersetzt und bleibt kurz: Ideen mit `idea_list`/`idea_read`
lesen, wenn der Nutzer darauf verweist; den Text des Nutzers nie ändern, sondern anmerken.

**Übergang:** `read_scratchpad` bleibt in Version 2.x als reiner Lese-Alias für `idea_list`
registriert und ist in der Beschreibung als veraltet markiert. So verliert keiner der 18 Agenten
den Lesezugriff, auch die Projekt-Agenten nicht, die neue Werkzeuge nicht automatisch bekommen.
`write_scratchpad` entfällt. Master erhalten die neuen Werkzeuge beim nächsten Dienststart von
selbst. Projekt-Agenten bekommen sie über die Agenten-Einstellungen (Admin).

## Etappe 2: Aus der Idee einen Task machen

- Knopf „Task anlegen“ im Detail. Titel ist die Kopfzeile, die Beschreibung des Tasks beginnt mit
  „Aus Idee <Kurz-ID>: <Kopfzeile>“ und enthält die Beschreibung der Idee. Projekt wird übernommen.
- Umsetzung nach dem Muster des Tickets-Moduls: direkter Eintrag in `module_tasks`, nur wenn die
  Tabelle existiert. Sonst zeigt `GET /meta` „Tasks nicht installiert“ und der Knopf fehlt.
- Die Idee merkt sich `task_id` und wechselt auf „Geplant“ (als Anmerkung festgehalten).
  Ein zweiter Task zur selben Idee wird abgelehnt (`task_already_linked`).
- Im Detail steht der verknüpfte Task mit Titel und Status. Ist der Task gelöscht, steht dort
  „Task nicht mehr vorhanden“ und der Knopf erscheint wieder.
- `idea_read` nennt den Task, damit der Agent den Zusammenhang kennt.
- Rückverweis (Nachtrag, tasks 1.3.0 und scratchpad 2.2.0): Der Task trägt die Idee als Herkunft
  in `module_tasks` (`source_kind` = `idea`, `source_id` = ID der Idee). Im Tasks-Reiter führt
  „Aus Idee“ auf `/scratchpad?idea=<id>`, `task_read` nennt die Herkunft. Ein Tasks-Modul ohne
  diese Spalten bekommt den Task wie bisher, nur ohne Rückverweis. Früher verknüpfte Tasks
  bekommen die Herkunft beim Laden der Ideenliste nachgetragen.

## Etappe 3: Blueprint-Entwurf zu einer Idee

Ablauf für den Nutzer: Idee schreiben → „Als Board skizzieren“ → der Agent zeichnet einen Entwurf →
Bausteine verschieben, streichen, ergänzen → der Agent liest die Fassung und schlägt die nächste
vor → wenn es passt: Task anlegen.

Änderungen am Blueprint-Modul:

- **Projekt am Board:** `002_project_proposal.sql` ergänzt `project_id`, `proposal_json`,
  `proposal_note`, `proposal_at`. Die Board-Liste lässt sich nach Projekt filtern.
- **Vorschlag statt Überschreiben:** Ein Board hat die Fassung des Nutzers (`graph_json`) und
  höchstens einen offenen Vorschlag des Agenten. Die Oberfläche zeigt ein Band „Vorschlag des
  Agenten“ mit Vorschau, „Übernehmen“ und „Verwerfen“. Beim Übernehmen wandert die bisherige
  Fassung in `module_blueprint_versions` (die letzten 20 je Board) und ist wiederherstellbar.
  Ist das Board leer, wird der Vorschlag direkt gezeichnet, weil nichts überschrieben wird.
- **Werkzeug `blueprint_propose`:** Der Agent liefert nur Inhalte, keine Koordinaten:
  `board` (ID oder Name) oder `name` für ein neues Board, `nodes` (Kürzel, Art, Beschriftung,
  Notiz, Platzhalter), `edges` (von, nach, bei Bedingungen ja/nein), `note` (was sich geändert hat).
  Geprüft werden bekannte Arten, eindeutige Kürzel, Verbindungen nur zwischen vorhandenen
  Bausteinen, höchstens 80 Bausteine und 2 MB.
- **Automatische Anordnung:** im Backend, ohne neue Bibliothek. Ablauf-Bausteine in Spalten von
  links nach rechts entlang der Verbindungen (Kreise werden aufgebrochen), Layout-Bausteine als
  eigener Stapel links daneben von oben nach unten. Verschiebt der Nutzer danach etwas, bleibt es so.
- **Neue Bausteine „Aufbau“** für „wie man es bauen könnte“: Modul, Schnittstelle, Datenbank/Tabelle,
  Datei, Agent-Werkzeug. Eigene Farbe. `render.py` und `boardText.ts` bekommen die dritte Gruppe
  (heute würden Bausteine einer unbekannten Gruppe im Text fehlen), der gemeinsame Testfall
  `board_text_case.json` wird erweitert.
- **Direktlink:** `/blueprint?board=<id>` öffnet das Board.
- **Chat neben dem Board:** rechts ein Chat-Fenster mit dem Agenten nach dem Muster von Game Studio
  und Storyteller, eine Sitzung je Board. Mit Projekt ist es der Projekt-Agent. Boards ohne
  Projekt haben keinen Chat (siehe „Nachträge aus dem Bau“). Die Seite fragt alle 5 Sekunden nach
  einem neuen Stand, auch ohne offenes Chat-Fenster. Fehlen dem Agenten `blueprint_read`,
  `blueprint_propose` oder `idea_read`, steht dort ein Hinweis; Admins können sie per Knopf
  ergänzen.

Änderungen am Ideen-Modul:

- Knopf „Als Board skizzieren“ im Detail legt ein Board mit dem Namen der Idee und ihrem Projekt an
  und merkt sich `board_id`. Danach heißt der Knopf „Board öffnen“.
- `idea_read` nennt das Board („lies es mit `blueprint_read`“). Der Chat neben dem Board startet mit
  dem Verweis auf Idee und Board.

### Nachträge aus dem Bau (PR #373, gemergt am 12.11.2026)

3a und 3b sind zusammen als blueprint 1.3.0 und scratchpad 2.3.0 ausgeliefert. Gegenüber dem Text
oben gilt:

- **Fassungszähler:** `002_project_proposal.sql` ergänzt zusätzlich `revision`. Die Zeichenfläche
  nennt beim Speichern den Stand, den sie kennt (`base_revision`); ist er überholt, antwortet die
  Route mit 409 `board_changed` und die Oberfläche bietet „Meine behalten“ oder „Neue laden“ an.
  „Meine behalten“ sichert die ersetzte Fassung vorher bei den früheren Fassungen (`keep_previous`).
  Grund: Die offene Zeichenfläche hätte einen direkt gezeichneten Entwurf des Agenten sonst
  überschrieben.
- **Zustands-Route:** `GET /boards/{id}/state` liefert nur `revision` und `proposal_at`. Die Seite
  fragt sie alle 5 Sekunden ab, solange ein Board offen ist, nicht nur bei offenem Chat.
- **Frühere Fassungen** tragen ihre Herkunft: `proposal` (Vorschlag übernommen), `restore`
  (Wiederherstellung), `overwrite` („Meine behalten“). Routen: `GET /boards/{id}/versions`,
  `POST /boards/{id}/versions/{version_id}/restore`.
- **Übernehmen gilt dem gesehenen Vorschlag:** `POST /boards/{id}/proposal/accept` nennt
  `proposal_at`. Hat der Agent inzwischen einen neuen Vorschlag abgelegt, antwortet die Route mit
  409 `proposal_changed`. Verwerfen: `DELETE /boards/{id}/proposal`.
- **Strengere Prüfung in `blueprint_propose`:** höchstens 400 Verbindungen; die Notiz zum Vorschlag
  höchstens 500 Zeichen; `event` und `note` haben keinen Eingang, `display` und `note` keinen
  Ausgang; Verbindungen aus einer Bedingung brauchen ja oder nein, andere dürfen es nicht tragen.
  Ein neues Board übernimmt das Projekt der Sitzung nur, wenn der Nutzer dort Zugriff hat.
- **Anordnung:** Aufbau-Bausteine stehen als eigenes Band unter dem Ablauf.
- **Board-Text:** Bausteine einer unbekannten Gruppe stehen beim Ablauf, statt zu fehlen.
  `blueprint_read` nennt einen offenen Vorschlag.
- **Chat neben dem Board:**
  - Routen `GET /boards/{id}/chat` (Agent, Grund wenn es keinen Chat gibt, fehlende Werkzeuge) und
    `POST /boards/{id}/chat` (Sitzung holen oder anlegen). Starten braucht Schreibrecht im Projekt
    (403 `project_read_only`).
  - **Kein Chat ohne Projekt.** Vorgesehen war dort der Buddy. Eine neue Sitzung mit dem Buddy würde
    auf der Buddy-Seite zur aktuellen Unterhaltung, solange dort keine gemerkt ist; verhindern lässt
    sich das nur im Kern. Entschieden am 12.11.2026: Es bleibt dabei, der Hinweis im Chat nennt den
    Weg (Board einem Projekt zuordnen).
  - **Einstiegstext statt Kontextübergabe:** Der Agent erfährt nicht von selbst, um welches Board
    es geht. Der Chat zeigt einen Text mit Board, Idee und Werkzeugen, den der Nutzer seiner ersten
    Nachricht voranstellt. Der Text ist deutsch, auch bei englischer Oberfläche.
  - **Breite:** 360 px bis 45 % des Fensters, ziehbar, im Browser gemerkt. Der Chat gibt nach, damit
    Palette und Zeichenfläche zusammen 480 px behalten. Reicht der Platz nicht für beide, liegt der
    Chat über dem Board und schließt, sobald der Nutzer „Vorschau“ oder „Frühere Fassungen“ wählt.
  - Scheitert das Ergänzen der Werkzeuge (zum Beispiel bei einem vom Modul verwalteten Agenten),
    steht der Grund am Hinweis.
- **Idee zu Board:** Die Route antwortet 201 für ein neues und 200 für das vorhandene Board, ohne
  Blueprint-Modul 409 `blueprint_not_installed`. Die Obergrenze des Blueprint-Moduls (200 Boards je
  Nutzer) gilt auch hier.

Nicht geprüft und bekannt offen: Im Chat neben dem Board wurde mit keinem echten Agenten
gearbeitet. Ist bei offenem Chat ein Baustein gewählt, wird die Zeichenfläche zwischen 1100 und
1300 px Fensterbreite schmal. Der Hilfe-Artikel im Kern fehlt noch.

## Etappe 4: Schlagworte, Suche, Spaltenansicht

- Schlagworte je Idee (freie Wörter, höchstens 10), Filter in der Liste, Vorschläge aus den schon
  benutzten.
- Suche über Kopfzeile und Beschreibung (einfache Teilwortsuche, keine Volltext-Tabelle).
- Spaltenansicht: eine Spalte je Status, Idee per Ziehen oder Auswahl in einen anderen Status.

## Sicherheit

- Besitzfilter in jeder Abfrage, auch in den Werkzeugen (`ctx.user_id`).
- Projektzugriff wird beim Schreiben geprüft, nicht nur in der Oberfläche.
- Zugriff auf `module_tasks` und `module_blueprint_boards` nur mit dem eigenen Nutzernamen.
- Inhalte der Ideen sind Nutzerdaten für den Agenten, keine Anweisungen (Hinweis in jeder Ausgabe).
- Größenbegrenzungen an Route und Werkzeug.
- Keine neuen Rechte, keine neuen Dienste, keine Abhängigkeiten.

## Tests

- pytest je Modul mit der Pflichtkopie `_hh_isolation.py`: Speicher (Besitz, Grenzen, Filter),
  Routen, Übernahme (auch zweiter Lauf, auch die Form der echten Daten), Werkzeuge (Text des Nutzers
  geschützt, Projekt-Standardfilter, Kürzung, leere ID), Task-Verknüpfung (mit und ohne Tasks-Tabelle),
  Anordnung (keine Überlappung, Kreis, Bedingung), Vorschlag (leer, nicht leer, übernehmen, verwerfen).
- vitest: Filtern, Gruppieren, Zählen, Speicherzustand, Board-Text mit der dritten Gruppe.
- Jeder Fund aus Review oder Live-Abnahme bekommt einen Test (Fix-Test-Regel).

## Auslieferung

| Etappe | Modul und Version | Kern |
|---|---|---|
| 1 Ideenliste | scratchpad 2.0.0 | Hilfe-Artikel `scratchpad.md` (de/en), Beschriftung „Ideen“ |
| 2 Idee zu Task | scratchpad 2.1.0 | – |
| 2 Nachtrag: Rückverweis vom Task zur Idee | tasks 1.3.0, scratchpad 2.2.0 | – |
| 3a Vorschläge, Anordnung, Aufbau-Bausteine | blueprint 1.3.0, scratchpad 2.3.0 | Hilfe-Artikel Blueprint (offen) |
| 3b Chat neben dem Board | in blueprint 1.3.0 enthalten (ein PR mit 3a) | – |
| 4 Schlagworte, Suche, Spalten | scratchpad 2.4.0 | – |

Die Etappen 1 und 2 sind ohne Blueprint nutzbar. Nach Etappe 2 wird entschieden, ob Etappe 3
gebaut wird: Blueprint wird bisher kaum genutzt, die Annahme „der Agent zeichnet den ersten Entwurf,
dann fällt die Hürde weg“ ist nicht gemessen. Anhaltspunkt: wie viele Ideen angelegt und wie viele
davon zu Tasks wurden.

## Risiken

- **Umstellung in einem Schritt:** Mit 2.0.0 ist der freie Zettel weg. Die alten Dateien bleiben als
  `.imported` liegen, ein Zurück auf 1.0.6 ist damit ohne Datenverlust möglich.
- **Agenten ohne neue Werkzeuge:** Projekt-Agenten bekommen sie nicht von selbst. Der Lese-Alias
  fängt das für das Lesen ab; Anmerken geht erst nach dem Ergänzen.
- **Direkter Zugriff auf Tabellen anderer Module** (Tasks, Blueprint): Ändert sich deren Aufbau,
  bricht die Verknüpfung. Abgefangen durch die Prüfung auf vorhandene Tabelle und Tests mit dem
  Tabellenaufbau der anderen Module.
- **Umfang von Etappe 1:** ein großer PR, weil Backend, Werkzeuge und Oberfläche zusammen wechseln.

## Ungeprüft, mit Prüfschritt

Derzeit nichts. Die beiden Prüfpunkte zu Etappe 3b sind geklärt (siehe unten).

## Geklärt am 12.11.2026

- **Symbol:** „Lightbulb“ ist in der installierten Symbolsammlung vorhanden (lucide-react 1.11.0)
  und wird über `moduleIcon` nach Namen geladen. Das Modul bekommt dieses Symbol.
- **Direktlink auf einen Task:** gibt es nicht. Das Tasks-Modul hat keine eigene Seite und keine
  Adresse je Task (nur Reiter im Workspace und Feld beim Buddy). Im Detail der Idee stehen deshalb
  Titel, Status und Kurz-ID des Tasks, kein Link.
- **README des Modul-Repos:** Die Tabelle der Module steht in `README.md` und `README.de.md`.
  Sie ist bei mehreren Modulen veraltet (Scratchpad 1.0.2 statt 1.0.6, Tasks 1.0.1 statt 1.2.1,
  Blueprint 1.0.2 statt 1.2.1). In Etappe 1 wird nur die Zeile des Scratchpads berichtigt.

- **Kontext für den Chat neben dem Board** (früher Prüfpunkt 1): Im Kern nachgelesen, nicht
  ausgeführt. Sitzungs-Metadaten erreichen den Agenten nicht, und die Chatansicht kennt keinen
  vorbelegten Text. Ein von außen gestarteter Lauf ginge nur über einen internen Helfer des Kerns,
  den ein Modul nicht aufrufen soll. Deshalb der Einstiegstext.
- **Buddy für Boards ohne Projekt** (früher Prüfpunkt 2): Der Buddy eines Nutzers lässt sich über
  die öffentliche Agenten-Konfiguration ermitteln. In der Testumgebung nachgestellt: Eine neue
  Sitzung mit ihm wird auf der Buddy-Seite zur aktuellen Unterhaltung. Deshalb kein Chat ohne
  Projekt.

## Nicht enthalten

- Freigabe von Ideen an andere Projektmitglieder.
- Verlauf von Kopfzeile und Beschreibung.
- Eigene Anmerkungen des Nutzers als Gesprächsfaden (die Tabelle lässt es später zu).
- Anhänge und Bilder an Ideen.
- Ein Generator, der aus einem Board Code erzeugt.
- Änderungen am Notizbuch- und am Diagramme-Modul.
