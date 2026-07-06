# Plan: Regie E1 — Screenplay-Planer (Kopf + Szenen + Reorder)

## Ziel
Nach E1 existiert im Atelier-Backend ein dateibasierter Drehbuch-Planer:
ein Screenplay-Kopf pro Projekt (Titel, Beschreibung, Film-/Audio-Modell,
Aspect-Ratio, Default-Dauer) und eine geordnete Liste von **Szenen**
(Beschreibung, Charaktere, Dialoge, Musik, Kamera-Presets), die man anlegen,
ändern, löschen und per Reorder umsortieren kann. **Kein Akt, kein Shot,
kein Agent, keine Generierung** — das ist E1.

## Bestehende Patterns (werden 1:1 gespiegelt)
- `storage.py`: `atelier_root(pid)`, `new_id()`, `is_valid_id()`, Directory-Helper.
- `characters.py`: `_read_json`/`_write_json`, `_sanitize()` mit Längen-Limits, CRUD.
- `routes.py`: `Auth`-Typ, `_guard(user, pid)`, pydantic `*In`-Models, `coded()`-Fehler.

## Dateien
- `backend/storage.py` — NEU: `screenplay_dir(pid)`, `scenes_dir(pid)` (Helper).
- `backend/screenplay.py` — NEU: CRUD für screenplay.json + Szenen + Reorder.
- `backend/routes.py` — NEU: Screenplay-/Szenen-Routen unter dem bestehenden Router.
- `tests/test_screenplay.py` — NEU: Storage/CRUD/Reorder + Guard/Traversal.

## Datenmodell (Teilmenge der SPEC-REGIE.md, ohne Akt/Shot)
```
atelier/screenplay/
  screenplay.json   { title, logline, description, film_model, audio_model,
                      voice_model, aspect_ratio, default_duration,
                      scene_order: [scene-id,...], created_at, updated_at }
  scenes/<id>.json  { id, title, description, character_ids: [...],
                      dialogues: [{character_id, line, emotion}],
                      music: {enabled, prompt, music_rel},
                      camera: {shot,lens,light,weather,time,mood},
                      location, time_of_day, created_at, updated_at }
```
> `scene_order` lebt im Kopf (screenplay.json) — eine einzige Quelle der Wahrheit
> für die Reihenfolge. Szenen-Dateien tragen KEINE Order (kein Split-Brain).

## Implementierungsreihenfolge (TDD)

### Task 1: Storage-Helper
- [ ] Test: `screenplay_dir`/`scenes_dir` legen Verzeichnis unter atelier_root an,
      liegen im Root (kein Traversal).
- [ ] Implementierung in `storage.py` (analog `characters_dir`).
- [ ] Commit: `feat(atelier/regie): storage helper screenplay/scenes dirs`

### Task 2: Screenplay-Kopf CRUD
- [ ] Test: `get_screenplay` liefert leeres Default wenn nichts existiert;
      `save_screenplay` sanitized (Längen-Limits) + persistiert; `updated_at` gesetzt.
- [ ] Implementierung `screenplay.py`: `get_screenplay`, `save_screenplay`,
      `_sanitize_head` (title≤200, logline≤500, description≤4000, Modelle≤200,
      aspect_ratio≤16, default_duration int 1..60, scene_order Liste valider IDs).
- [ ] Commit: `feat(atelier/regie): screenplay head crud`

### Task 3: Szenen CRUD
- [ ] Test: create legt Szene an + hängt ID an scene_order; get/list; update merged;
      delete entfernt Datei + ID aus scene_order; ungültige ID → None.
- [ ] Implementierung: `list_scenes` (in scene_order-Reihenfolge!), `get_scene`,
      `create_scene`, `update_scene`, `delete_scene`, `_sanitize_scene`
      (dialogues: je {character_id≤32, line≤2000, emotion≤50}, max 100;
       character_ids max 32; music.prompt≤1000; camera dict aus bekannten Keys).
- [ ] Commit: `feat(atelier/regie): scene crud`

### Task 4: Reorder
- [ ] Test: `reorder_scenes` akzeptiert Permutation vorhandener IDs, ignoriert
      unbekannte IDs, ergänzt fehlende ans Ende (robust gegen Client-Drift).
- [ ] Implementierung: `reorder_scenes(pid, ordered_ids)` schreibt scene_order.
- [ ] Commit: `feat(atelier/regie): scene reorder`

### Task 5: Routen
- [ ] Test: GET/PUT screenplay; GET/POST/PUT/DELETE scenes; POST scenes/reorder —
      je mit `_guard` (fremdes Projekt → 404). TestClient wie test_audio.py.
- [ ] Implementierung in `routes.py`: pydantic-Models
      (`ScreenplayIn`, `SceneIn`, `ReorderIn`), Routen analog Charakter-Block.
- [ ] Commit: `feat(atelier/regie): screenplay + scene routes`

## Akzeptanzkriterien
- [ ] Screenplay-Kopf speichern/laden funktioniert, Default wenn leer.
- [ ] ≥2 Szenen anlegen, ändern, löschen, umordnen — alles persistent nach Reload.
- [ ] `scene_order` ist einzige Reihenfolge-Quelle; delete räumt sie mit auf.
- [ ] Guard greift (fremdes/ungültiges Projekt → 404); kein Path-Traversal.
- [ ] Alle neuen Tests grün, bestehende atelier-Tests unberührt, ruff clean.

## Nicht in diesem Plan (kommt in E2+)
- Akt-Ebene (B), Shot-Ebene, Regieagent-Zerlegung, Batch-Render.
- Frontend/Regie-Tab (E2) — E1 ist reines Backend + Tests.
- Musik tatsächlich generieren, Dialog-TTS — nur Datenfelder, keine Aktion.
```
