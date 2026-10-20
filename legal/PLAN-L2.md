# Bauplan L2 – Fall = Projekt, Fallakte, Fristen, Rechts-Agent

Spec: `legal/SPEC-LEGAL.md` §4.2–4.4, §4.6 · Task f0b8d254 · Version 0.2.0 · Stand 20.10.2026

**Ziel L2:**
- „Neuer Fall“ legt ein **Projekt** samt Fallakte und einem **Rechts-Agenten** an. Mitglieder des Projekts sehen den
  Fall mit ihrer Rolle.
- Fristen rechnet ein Rechner **ohne KI** nach §§ 187, 188, 193 BGB, mit Feiertagen des gewählten Bundeslandes.
- Der Agent liest den Fall und legt **nur Vorschläge** ab. Erst der Mensch übernimmt sie.
- Briefe (L3), Zitat-Prüfer und Rechtsprechung (L4) gehören nicht zu L2.

## Befunde vor dem Bau (geprüft 20.10.2026)

- **Projekt anlegen wie Storyteller** (`storyteller/backend/team/setup.py`): `projects.config.create(name, llm_model,
  created_by, metadata)` legt Projekt, Arbeitsordner und **Projekt-Agent** an. Danach setzt das Modul Werkzeuge,
  Name und Anweisung des Agenten mit `agents.config.update` und `set_system_prompt`. Scheitert ein Schritt, wird das
  Projekt wieder gelöscht (der Kern löscht den Agenten mit).
- **Standard-Werkzeuge eines Projekt-Agenten** (`agents/_defaults.py`): `shell_exec, file_read, file_write, file_patch,
  fetch_url, …`. Für den Rechts-Agenten werden sie **ersetzt**:
  - Liste: `legal_*`, `web_search`, `read_memory`, `write_memory`, `search_memory`, `todo_write`, `list_skills`, `load_skill`
  - **Keine Außenwirkung**: `shell_exec`, `fetch_url` und `web_browser` stehen in `db/_mirror_groups.OUTWARD_TOOLS`.
  - **Keine Datei-Werkzeuge.**
  - `web_search` zählt nicht zur Außenwirkung (nur Suche, keine Zieladresse).
- **Agent-Werkzeuge ändern** darf in der API nur der Admin (`PATCH /api/agents/{id}`, `require_admin`). Ein Nutzer mit
  `legal.create_case` kann dem Agenten also nachträglich keine Shell geben.
- **Projekt-Briefing** (`runner/_run_workspace.project_briefing`) kommt in den Systemprompt. Der Fall-Kurztext steht
  deshalb in der Projektbeschreibung. Den ausführlichen Sachverhalt liest der Agent mit `legal_case`.
- **Fristen** (Wortlaut gesetze-im-internet.de, 20.10.2026):
  - § 187 Abs. 1: Ereignistag zählt nicht mit. Abs. 2: Tagesbeginn zählt mit.
  - § 188 Abs. 1: Tagesfrist endet mit Ablauf des letzten Tages.
  - § 188 Abs. 2: Wochen- und Monatsfrist endet am Tag gleicher Benennung oder Zahl. Bei § 187 Abs. 2 ist es der Vortag.
  - § 188 Abs. 3: Fehlt der Tag im letzten Monat, endet die Frist am Monatsletzten.
  - § 193: Fällt das Ende auf Sonnabend, Sonntag oder einen am Erklärungsort staatlich anerkannten allgemeinen
    Feiertag, gilt der nächste Werktag.
- **Feiertage**: Grundlage ist die DGB-Übersicht 2026–2028 („ohne Gewähr“). Die Osterformel (Gauß) stimmt dort für
  2026, 2027 und 2028 mit allen beweglichen Feiertagen und dem Buß- und Bettag überein (geprüft).
  - **Nur gemeindeweise** und damit **nicht automatisch** eingerechnet:
    - Fronleichnam in Sachsen und Thüringen
    - Mariä Himmelfahrt in Bayern
    - Augsburger Friedensfest
  - Der Rechner weist bei diesen Fällen ausdrücklich darauf hin. Eine Gemeindeliste gehört nicht in L2.

## Datenmodell (`migrations/002_cases.sql`)

```
module_legal_cases       project_id PK, title, area, status(open|waiting|done), state(BL-Kürzel), summary, facts,
                         goal, our_ref, their_ref, created_by, created_at, updated_at
module_legal_parties     id, project_id, role(opponent|lawyer|authority|court|witness|me|other), name, address,
                         contact, note, created_at
module_legal_deadlines   id, project_id, label, event_date, kind(days|weeks|months|years|date), amount, start_rule
                         (event|day_start), due_date, calc(JSON: Rechenweg), status(open|done|missed), note, created_at
module_legal_notes       id, project_id, author(agent|user), agent_name, title, body, citations(JSON), created_at
module_legal_proposals   id, project_id, kind(party|deadline|fact|note), payload(JSON), author_agent, status(open|
                         accepted|rejected), created_at, decided_by, decided_at
```

- Alles in der Kern-DB, nichts im Projektordner. Begründung: Projekt-Agenten hätten sonst über Datei-Werkzeuge
  Zugriff vorbei an der Vault-PIN.
- Löschen des Projekts: Ein Job räumt Fälle ohne Projekt nach 30 Tagen weg, vorher Sicherung als JSON nach
  `data_dir/legal/archive/` (Spec §4.2).

## Schritte (TDD, rote Tests als eigener Commit)

1. **Fristen** (`deadlines.py`, `holidays_de.py`). Tests mit 25 Handfällen, die Erwartung steht jeweils im Testtext
   mit Begründung:
   - Tage, Wochen, Monate, Jahre
   - § 188 Abs. 3 (31.01. + 1 Monat → 28.02. bzw. 29.02.)
   - § 193: Sa/So → Mo, Feiertag → nächster Werktag, Kette aus Feiertag und Wochenende
   - Bundesländer:
     - Reformationstag in NI, nicht in NW
     - Fronleichnam in NW, nicht in NI
     - Buß- und Bettag nur SN
     - Frauentag BE und MV
     - Weltkindertag TH
   - § 187 Abs. 2 (Tagesbeginn)
   - Hinweis bei gemeindeweisen Feiertagen
   - Rechenweg-Text
   - Ungültige Eingaben
2. **Fälle anlegen** (`cases.py`): Projekt, Fall, Agent mit fester Werkzeugliste und Anweisung, Rückbau bei Fehler.
   Tests:
   - Ohne `legal.create_case` gibt es 403.
   - Ergebnis enthält genau ein Projekt, einen Agenten und einen Fall.
   - Die Werkzeuge des Agenten schneiden sich nicht mit `OUTWARD_TOOLS` und enthalten keine Datei-Werkzeuge.
   - Scheitert ein Schritt, bleibt kein Projekt übrig.
   - Projekt-Metadaten enthalten `{"legal": {"case": true}}`.
3. **Zugriff** (`access.py`, wie `storyteller/_files.project_access`): Projektrolle `read`, `write` oder `admin`,
   System-Admin darf alles. Tests: Nicht-Mitglied → 404, `read` darf lesen und nicht schreiben, `write` darf beides.
4. **Routen**:
   - `/cases` (Liste nur der eigenen bzw. Mitglieds-Fälle), `POST /cases`, `/cases/{pid}` lesen und ändern
   - `/cases/{pid}/parties|deadlines|notes|proposals` (CRUD bzw. übernehmen/verwerfen)
   - `/deadline/calc` (Rechner ohne Fall)
   - Alle `/cases/{pid}`-Routen prüfen die Projektrolle.
5. **Werkzeuge**:
   - `legal_case` (lesen)
   - `legal_deadline` (rechnen, speichert nichts)
   - `legal_propose_party`, `legal_propose_deadline`, `legal_propose_fact`, `legal_note`
   - Alle nur für `ToolContext.project_id`, Rechte laut Projektrolle wie bei Storyteller `scope()`.
   - **`sensitive_tools`: alle Fall-Werkzeuge `privat`.**
   - Tests: ohne Projekt Fehler, fremdes Projekt Fehler, `read`-Rolle darf nichts vorschlagen, Vorschlag ändert die
     Akte nicht.
6. **Aufräum-Job** für verwaiste Fälle mit Sicherung. Test: Projekt weg, nach 30 Tagen Sicherung + Löschung, vorher nicht.
7. **Frontend**:
   - Reiter **Fälle**: Liste mit Ampel der nächsten Frist, „Neuer Fall“ mit Aufnahmeformular (Was ist passiert, seit
     wann, wer ist beteiligt, Ziel, Bundesland, bekannte Fristen)
   - **Fallakte** mit Reitern Übersicht, Beteiligte, Fristen (mit Rechner), Notizen, Vorschläge (übernehmen/verwerfen)
   - Knopf „Mit dem Rechts-Agenten sprechen“ öffnet den Projekt-Chat
   - vitest: Ampel, Rechenweg-Anzeige, Formularprüfung

## Prüfung vor dem PR

- pytest, ruff, `check_test_safety`, `check_version_bump`, vitest/tsc/eslint im Kern-Worktree.
- **Mutanten**:
  - § 187-Startregel
  - § 188 Abs. 3
  - § 193 Sonnabend
  - Feiertag je Land
  - Osterdatum
  - Rolle `read` darf schreiben
  - Agent bekommt `shell_exec`
  - fremdes Projekt im Werkzeug
  - Vorschlag schreibt direkt
  - Aufräum-Job vor 30 Tagen
- **Live auf hydratest**:
  - Fall „Mietsache Hitze“ anlegen: Projekt + Agent + Akte
  - zweiter Nutzer als `read`-Mitglied sieht den Fall, ändert nichts
  - Agent im Chat: liest den Fall, sucht § 536c BGB, berechnet „14 Tage ab Zugang Do 22.10.2026, NRW“ → Ende
    Do 05.11.2026 (Allerheiligen So 01.11. liegt innerhalb der Frist und verschiebt nichts), legt eine Frist als Vorschlag ab
  - Mensch übernimmt den Vorschlag
  - Browser-Rundlauf
