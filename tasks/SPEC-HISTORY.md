# Tasks: Verlauf statt Überschreiben

Task df2f2eb2. Freigabe Till am 30.09.2026: Verlauf + `note` + Anzeige + Wiederherstellung.
Nur Anhängen wurde bewusst verworfen (Texte wachsen endlos, Korrekturen unmöglich).

## Problem

`task_write` mit `task_id` und `description` ersetzt die Beschreibung per UPDATE.
Die alte Fassung ist danach weg. Seit August bei 212 Tasks belegt (~190.000 Zeichen).
Agenten nutzen die Beschreibung wie ein Protokoll und überschreiben dabei die Analyse.

## Datenmodell

Migration `002_task_history.sql`:

```sql
module_tasks_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL REFERENCES module_tasks(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  changed_at TEXT NOT NULL,      -- wann diese Fassung ersetzt wurde (bzw. gesehen, bei Wiederherstellung)
  source TEXT NOT NULL           -- 'update' | 'restored'
)
```

Index auf `(task_id, changed_at)`. Löschen eines Tasks löscht seinen Verlauf mit.

## Verhalten

- `service.update_task`: ändert sich Titel oder Beschreibung wirklich (neuer Wert ≠ alter Wert),
  wird VORHER die alte Fassung (Titel + Beschreibung) in den Verlauf geschrieben, in derselben
  Transaktion. Reine Status-/Prioritätswechsel erzeugen keinen Eintrag.
- Neuer Parameter `note`: hängt an die Beschreibung einen Absatz an:
  `\n\n[YYYY-MM-DD HH:MM] <note>`. Das ist eine Änderung der Beschreibung und landet damit
  ebenfalls im Verlauf. `note` und `description` zusammen: erst ersetzen, dann anhängen.
  Leere `note` wird ignoriert.
- `service.history(username, task_id)`: Verlauf neueste zuerst, nur für eigene Tasks.
- Schutz: höchstens 200 Verlaufseinträge pro Task. Beim 201. wird der älteste
  `update`-Eintrag entfernt, `restored`-Einträge bleiben.

## Tool `task_write`

- Neues Feld `note` (Beschreibung: „Hängt eine datierte Notiz an. Normalfall für Fortschritt,
  Befunde, Status-Notizen.“).
- `description` wird beschrieben als „ERSETZT die Beschreibung. Nur für bewusste Korrekturen.
  Die alte Fassung bleibt im Verlauf.“
- Prompt-Hinweis ergänzt: „Fortschritt → note, nicht description.“

## Tool `task_read`

- Zeigt `Verlauf: N frühere Fassungen` wenn N > 0.
- Neues Feld `history` (bool): liefert zusätzlich alle früheren Fassungen mit Zeitpunkt und Quelle.

## API / Oberfläche

- `PATCH /tasks/{id}` akzeptiert `note`.
- `GET /tasks/{id}/history`: Verlauf (nur eigene Tasks, sonst 404).
- `GET /tasks` liefert je Task `history_count`.
- Task-Panel: „Verlauf (N)“ aufklappbar unter der Beschreibung.

## Wiederherstellung (separates Skript, nach Deploy + Tills OK)

`_work/task-history/restore.py`: liest `_work/triage/task-texte-verloren-2026-09-30.json`,
schreibt je fehlender Fassung einen Eintrag `source='restored'` mit dem Zeitpunkt aus dem Chat.
Aktuelle Beschreibungen bleiben unverändert. Trockenlauf zuerst, DB-Backup vorher,
Zählung vorher/nachher, idempotent (gleiche Fassung nicht doppelt).

## Nicht in diesem Umfang

- Verlauf im Ticket-Modul (tickets schreibt module_tasks nur per INSERT).
- Wiederherstellen einer alten Fassung per Klick.
