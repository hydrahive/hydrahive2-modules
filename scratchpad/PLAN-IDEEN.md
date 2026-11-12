# Plan: Scratchpad wird Ideen

Gehört zu `SPEC-IDEEN.md` (Task 954f2958). Stand 12.11.2026: Entwurf, noch nichts gebaut.

## Ziel

Nach diesem Plan gibt es im Modul `scratchpad` einzelne Ideen mit Kopfzeile, Beschreibung, Projekt
und Status statt eines Freitexts. Aus einer Idee wird per Knopf ein Task. Der Agent merkt an Ideen
an und zeichnet auf Wunsch ein Blueprint-Board dazu.

## Regeln für jeden Schritt

- Erst der Test, rot gesehen, dann der Code, grün gesehen. Ein Commit je Schritt.
- Keine Datei über 200 Zeilen. Kein `print`. Pfade nur über `settings`.
- Jeder Modul-PR hebt die Version im Manifest an. Reine `.md`-PRs nicht.
- Modul-Tests laden `tests/_hh_isolation.py` zuerst. Kein `DELETE` ohne `WHERE`, kein `rmtree`.
- Vor jedem PR: Modul-Tests, `scripts/check_test_safety.py`, `scripts/check_version_bump.py`,
  Frontend-Tests und Typprüfung im Kern-Checkout.
- Live wird es erst über den Update-Knopf. Merges und Neustarts nur mit Tills OK.

## Was nicht brechen darf

- `scratchpad/frontend/farbstufen.test.ts` und `saveState.test.ts`.
- Im Kern: `tileArt.test.ts`, `vaultAreas.test.ts`, `AreaTopbar.test.tsx` (verwenden `/scratchpad`).
  Die Adresse bleibt, also bleiben sie gültig.
- `tasks/tests` und `blueprint/tests` (bestehende Suiten der Nachbarmodule).
- Lesezugriff der 18 Agenten mit `read_scratchpad`.

## Etappe 1: Ideenliste (scratchpad 2.0.0)

Dateien neu:

- `migrations/001_ideas.sql`: beide Tabellen und Indizes
- `backend/store.py`: Ideen und Anmerkungen lesen und schreiben, Besitzfilter, Grenzen, Zählung
- `backend/access.py`: Projektzugriff des Nutzers
- `backend/legacy_import.py`: alte Dateien in Ideen umwandeln
- `backend/tools_read.py`: `idea_list`, `idea_read`, Alias `read_scratchpad`
- `backend/tools_write.py`: `idea_write`
- `backend/_ids.py`: Kurz-ID auflösen
- `backend/render.py`: Idee als Text für den Agenten
- `tests/_hh_isolation.py`, `tests/conftest.py`, `pytest.ini`, `tests/test_*.py`
- `frontend/types.ts`, `frontend/ideaView.ts`, `frontend/useIdeas.ts`
- `frontend/IdeasPage.tsx`, `frontend/components/{IdeaForm,IdeaList,IdeaDetail,IdeaNotes}.tsx`
- `frontend/texts.de.ts`, `frontend/texts.en.ts`

Dateien geändert: `backend/__init__.py`, `backend/routes.py`, `frontend/api.ts`,
`frontend/index.tsx`, `frontend/saveState.ts`, `manifest.json`.
Dateien entfernt: `backend/service.py`, `backend/tools.py`, `frontend/ScratchpadPage.tsx`.

### 1.1 Test-Gerüst

- [ ] `tests/_hh_isolation.py` als Kopie von `scripts/_hh_isolation.py`, `conftest.py` nach dem
      Vorbild von `tasks/tests/conftest.py`, `pytest.ini`.
- [ ] Ein Test, der prüft, dass `settings.data_dir` im Test-Verzeichnis liegt. Grün.
- [ ] `python3 scripts/check_test_safety.py` meldet das Modul ohne Verstoß.

### 1.2 Speicher

- [ ] Tests: anlegen und lesen; fremde Idee unsichtbar; Liste nach Projekt, „ohne Projekt“ und
      Status; Zählung je Status; ändern; löschen entfernt Anmerkungen mit; Titel leer, Titel zu lang,
      Beschreibung zu lang, mehr als 2.000 Ideen jeweils mit benanntem Fehler.
- [ ] `001_ideas.sql` und `store.py`.

### 1.3 Projektzugriff

- [ ] Tests: Mitglied darf, Fremder bekommt `project_not_found`, Admin darf, ohne Projekt erlaubt,
      unbekannte Projekt-ID abgelehnt.
- [ ] `access.py` mit `role_of` aus dem Kern, eingebunden in Anlegen und Ändern.

### 1.4 Übernahme der alten Dateien

- [ ] Tests: Datei mit drei Überschriften ergibt drei Ideen; Datei ohne Überschrift ergibt eine;
      Titel aus erster Zeile; Trennlinien fallen weg; Herkunft je Datei; zweiter Lauf legt nichts
      doppelt an; Dateien heißen danach `.imported`; leere und fehlende Dateien; ein Testfall in der
      Form der echten Daten vom 12.11.2026.
- [ ] `legacy_import.py`, aufgerufen vor der ersten Liste eines Nutzers.

### 1.5 Routen

- [ ] Tests: `GET /meta`; anlegen, lesen, ändern, löschen; Filter; 404 bei fremder Idee;
      422 bei ungültigem Status; Anmerkung löschen; ohne Anmeldung 401.
- [ ] `routes.py` neu. Die drei alten Routen entfallen.

### 1.6 Werkzeuge

- [ ] Tests `idea_list`: Standardfilter ist das aktive Projekt, `*` zeigt alle, seitenweise, leer.
- [ ] Tests `idea_read`: volle ID, Kurz-ID, mehrdeutig, leere ID abgelehnt, Kürzung, Hinweis
      „Vorgaben des Nutzers“ im Text.
- [ ] Tests `idea_write`: neue Idee hat Herkunft Agent; Anmerkung anhängen; Status ändern schreibt
      Anmerkung; Titel oder Beschreibung einer Nutzer-Idee ändern schlägt fehl mit Hinweis auf `note`;
      bei einer Agent-Idee erlaubt.
- [ ] Test Alias: `read_scratchpad` liefert dieselbe Liste und ist als veraltet beschrieben.
- [ ] `tools_read.py`, `tools_write.py`, `_ids.py`, `render.py`, Anmeldung in `__init__.py`.

### 1.7 Manifest

- [ ] Version 2.0.0, Name „Ideen“, neue Beschreibung, Symbol „Lightbulb“.

### 1.8 Oberfläche

- [ ] vitest `ideaView.test.ts`: filtern, nach Projekt gruppieren, je Status zählen, sortieren.
- [ ] vitest `saveState.test.ts` an die neuen Fehlernamen angepasst.
- [ ] `types.ts`, `api.ts`, `ideaView.ts`, `useIdeas.ts`.
- [ ] `IdeaForm.tsx`: Kopfzeile, Beschreibung, Projektauswahl mit gemerkter Wahl, Strg+Enter.
- [ ] `IdeaList.tsx`: Filter, Gruppen, Marken, Zähler, leerer Zustand.
- [ ] `IdeaDetail.tsx` und `IdeaNotes.tsx`: bearbeiten mit automatischem Speichern, Status, Projekt,
      Anmerkungen, Löschen mit Rückfrage.
- [ ] `IdeasPage.tsx` und `index.tsx` (Adresse `/scratchpad`, Texte de und en).
- [ ] Typprüfung und Bau im Kern-Checkout grün.

### 1.9 Begleitende Änderungen

- [ ] README des Modul-Repos in beiden Sprachen: nur die Zeile des Scratchpads (Name, Version,
      Werkzeuge, Beschreibung). Die übrigen veralteten Zeilen sind nicht Teil dieses Plans.
- [ ] Kern-PR: Hilfe-Artikel `scratchpad.md` de und en neu geschrieben, Beschriftung in `help.json`,
      Text der Aktion „Idee merken“, Verknüpfung auf der Buddy-Seite.

### 1.10 Abnahme

- [ ] Nach dem Update: die vier übernommenen Ideen stehen in der Liste, die alten Dateien heißen
      `.imported`.
- [ ] Idee anlegen, Projekt und Status ändern, löschen. Als zweiter Nutzer ist nichts davon sichtbar.
- [ ] Ein Agent liest die Ideen und hängt eine Anmerkung an; der Text des Nutzers ist unverändert.

## Etappe 2: Idee zu Task (scratchpad 2.1.0)

Dateien: `backend/task_link.py` (neu), `backend/routes.py`, `backend/render.py`,
`frontend/components/IdeaTask.tsx` (neu), `frontend/api.ts`, Texte, `manifest.json`.

- [ ] Tests: Task entsteht mit Titel, Beschreibung, Projekt und Nutzer; Idee merkt sich `task_id`
      und steht auf „Geplant“ mit Anmerkung; zweiter Versuch `task_already_linked`; ohne Tabelle
      `module_tasks` meldet `GET /meta` „nicht installiert“ und die Route antwortet 409;
      gelöschter Task wird als fehlend gemeldet; fremde Idee 404.
- [ ] `task_link.py` nach dem Muster von `tickets/backend/task_link.py`, Route `POST /ideas/{id}/task`.
- [ ] `idea_read` nennt Titel und Status des Tasks (Test).
- [ ] Knopf und Anzeige im Detail: Titel, Status und Kurz-ID des Tasks (kein Link, das Tasks-Modul
      hat keine Adresse je Task).
- [ ] Abnahme: Idee zu Task, Task erscheint im Tasks-Modul unter dem richtigen Projekt.

## Nachtrag zu Etappe 2: Rückverweis (tasks 1.3.0, scratchpad 2.2.0)

Dateien Tasks: `migrations/003_task_source.sql`, `backend/tools/task_read.py`,
`frontend/components/TaskSource.tsx` (neu), `frontend/components/TaskPanel.tsx`, `frontend/types.ts`.
Dateien Ideen: `backend/task_link.py`, `backend/routes.py`, `frontend/IdeasPage.tsx`,
`frontend/ideaView.ts`, `frontend/useIdeas.ts`.

- [ ] Tests und Migration: `source_kind` und `source_id` in `module_tasks`, bestehende Tasks
      behalten ihre Daten, über die Routen des Tasks-Moduls nicht setzbar.
- [ ] `task_read` nennt die Herkunft, der Tasks-Reiter zeigt „Aus Idee“.
- [ ] Ideen schreiben die Herkunft beim Anlegen, auch gegen ein Tasks-Modul ohne die Spalten (Test).
- [ ] Früher verknüpfte Tasks bekommen die Herkunft nachgetragen (Test).
- [ ] `/scratchpad?idea=<id>` öffnet die Idee und stellt die Filter passend.
- [ ] Abnahme: im Tasks-Reiter auf „Aus Idee“ klicken, die Idee geht auf.

## Entscheidungspunkt nach Etappe 2

Mit Till: Wird Etappe 3 gebaut? Anhaltspunkt sind die angelegten Ideen und die daraus entstandenen
Tasks seit Etappe 1.

Entschieden am 12.11.2026: Etappe 3 wird gebaut.

## Etappe 3a: Vorschläge im Blueprint (blueprint 1.3.0, scratchpad 2.3.0)

Dateien Blueprint: `migrations/002_project_proposal.sql`, `migrations/003_versions.sql`,
`backend/layout.py`, `backend/proposal.py`, `backend/tools_propose.py`, `backend/versions.py` (neu);
`backend/store.py`, `backend/routes.py`, `backend/render.py`, `backend/__init__.py`,
`frontend/palette-data.ts`, `frontend/nodes.tsx`, `frontend/boardText.ts`,
`frontend/board_text_case.json`, `frontend/BlueprintPage.tsx`, `frontend/BoardSidebar.tsx`,
`frontend/ProposalBanner.tsx` (neu), `frontend/api.ts`, `manifest.json`.
Dateien Ideen: `backend/board_link.py` (neu), `backend/routes.py`, `backend/render.py`,
`frontend/components/IdeaBoard.tsx` (neu).

- [ ] Tests Anordnung: Kette steht in Spalten von links nach rechts; Verzweigung einer Bedingung;
      Kreis bricht nicht ab; Layout-Bausteine als Stapel; keine zwei Bausteine überlappen;
      gleiche Eingabe ergibt gleiche Positionen.
- [ ] `layout.py`.
- [ ] Tests Vorschlag: unbekannte Art, doppeltes Kürzel, Verbindung ins Leere, mehr als
      80 Bausteine jeweils abgelehnt; leeres Board wird direkt gezeichnet; nicht leeres Board
      bekommt einen Vorschlag und `graph_json` bleibt gleich; übernehmen legt die alte Fassung in
      die Versionen; verwerfen löscht nur den Vorschlag; nach 21 Übernahmen liegen 20 Versionen vor;
      fremdes Board unsichtbar.
- [ ] Migrationen, `proposal.py`, `versions.py`, Routen für Übernehmen, Verwerfen, Versionen,
      Projektfilter.
- [ ] Tests und Code `blueprint_propose` (Werkzeug), Anmeldung, Hinweis im System-Prompt.
- [ ] Bausteine „Aufbau“: Test für `render.py` und `boardText.ts` am erweiterten gemeinsamen
      Testfall (dritte Gruppe erscheint), dann Palette, Farben, Knoten.
- [ ] Oberfläche: Band „Vorschlag des Agenten“ mit Vorschau, Direktlink `?board=`, Projektfilter.
- [ ] Ideen: Tests und Code `board_link.py` (Board mit Name und Projekt der Idee, zweiter Aufruf
      liefert dasselbe Board, ohne Blueprint 409), Knopf im Detail, `idea_read` nennt das Board.
- [ ] Abnahme: Idee anlegen, Board skizzieren lassen (Auftrag im Chat), Vorschlag übernehmen,
      Bausteine verschieben, zweiten Vorschlag verwerfen, alte Fassung wiederherstellen.

## Etappe 3b: Chat neben dem Board (blueprint 1.4.0)

- [ ] Versuch (Prüfpunkt 1 der Spec): Kommt Kontext aus den Sitzungs-Metadaten beim Agenten an, und
      zeigt `ChatPane` einen von außen gestarteten Lauf? Ergebnis in die Spec schreiben, dann den
      Weg festlegen. Rückfall: Einstiegstext zum Kopieren.
- [ ] Tests: Sitzung je Board wird wiederverwendet; mit Projekt der Projekt-Agent, ohne Projekt der
      Buddy; Nutzer ohne Schreibrecht im Projekt kann nicht starten; fehlende Werkzeuge werden gemeldet.
- [ ] `backend/chat.py`, Routen, `frontend/AgentDock.tsx` nach dem Vorbild von Game Studio.
- [ ] Abfrage nach neuem Vorschlag alle 5 Sekunden, solange das Fenster offen ist (Test mit
      gestellter Uhr).
- [ ] Abnahme: Idee → Board → im Chat „zeig mir, wie es ablaufen würde“ → Vorschlag erscheint ohne
      Neuladen.

## Etappe 4: Schlagworte, Suche, Spalten (scratchpad 2.4.0)

- [ ] `migrations/002_tags.sql`, Tests und Code für Schlagworte (höchstens 10, Vorschläge).
- [ ] Tests und Code für die Suche `q` über Kopfzeile und Beschreibung.
- [ ] vitest und Code für die Spaltenansicht, Statuswechsel per Ziehen und per Auswahl.

## Reihenfolge der PRs

1. Dieser PR: Spec und Plan (nur `.md`).
2. Modul-PR Etappe 1 und Kern-PR für Hilfe und Beschriftung. Erst der Modul-PR, dann der Kern-PR.
3. Modul-PR Etappe 2, danach Modul-PR Rückverweis (tasks 1.3.0, scratchpad 2.2.0).
4. Nach der Entscheidung: Modul-PR Blueprint 3a, danach Modul-PR Ideen 2.3.0, danach 3b.
5. Modul-PR Etappe 4.

## Akzeptanzkriterien

- [ ] Eine Idee ist in zwei Feldern und ohne Agent angelegt und einem Projekt zugeordnet.
- [ ] Die Liste lässt sich nach Projekt und Status filtern und zeigt die Anzahl je Status.
- [ ] Der freie Zettel ist weg, die alten Inhalte stehen als Ideen in der Liste.
- [ ] Der Agent kann den Text einer Idee des Nutzers nicht ändern (Test).
- [ ] Aus einer Idee entsteht ein Task mit Verweis in beide Richtungen.
- [ ] Der Agent legt einen Board-Vorschlag ab, ohne die Fassung des Nutzers zu überschreiben (Test).
- [ ] Alle Suiten grün, keine Datei über 200 Zeilen, Versionen angehoben.

## Nicht in diesem Plan

Siehe Abschnitt „Nicht enthalten“ der Spec.
