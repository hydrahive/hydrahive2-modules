# Plan: Regie E4 — Regieagent (Szenen → Shots, Storyboard-Vorschau)

## Ziel
Nach E4 kann der User ein fertiges Drehbuch (Kopf + Szenen aus E1/E2) an einen
**Regieagenten** schicken. Der zerlegt jede Szene per LLM in konkrete **Shots**
(Kamera-Einstellung, präziser englischer Video-Prompt, beteiligte Charaktere,
Dauer) und legt sie als Vorschau ab — **ohne** etwas zu generieren. Der User
prüft/editiert die Shots. Batch-Render (Phase 2) ist E5.

## Bestehende Bausteine
- `screenplay.py` (E1): Kopf + Szenen-CRUD, Sanitizing-Muster, `_read_json`/`_write_json`.
- `storage.py`: `screenplay_dir`, `new_id`, `is_valid_id`.
- Core `hydrahive.llm.client.complete(messages, model, temperature, max_tokens)` — LLM-Aufruf (alle Provider).
- `characters.py`: `list_characters()`/`get_character()` — Steckbriefe + Style-Anchors für den Prompt-Bau.
- Kamera-Preset-Katalog (`presets.py`) — der Agent wählt gültige Preset-Keys.

## Datenmodell — Shots (neu)
```
atelier/screenplay/shots/<scene-id>.json   # Liste der Shots EINER Szene
  [ { id, scene_id, order, shot (Kamera-Key), prompt (engl.),
      character_ids: [...], duration, status: "planned" } ]
```
> Shots liegen pro Szene in EINER Datei (`shots/<scene-id>.json`) — einfache
> Liste, Reihenfolge = Array-Index. Beim Zerlegen wird die Datei überschrieben.

## Ablauf (2 Phasen, User-Gate dazwischen)
- **Phase 1 (E4):** `decompose` → Agent zerlegt ALLE Szenen → schreibt `shots/*`
  mit status `planned`. Kein Generieren. Frontend zeigt Storyboard-Vorschau.
- **User-Gate:** Shots editierbar/löschbar (CRUD), dann „Freigeben" (E5).
- **Phase 2 (E5):** Batch-Render. NICHT in diesem Plan.

## Implementierungsreihenfolge (TDD)

### Task 1: Shot-Storage + CRUD (`director.py`)
- [ ] Test: `get_shots(pid, scene_id)` leer→[]; `save_shots` sanitized+persistiert;
      `update_shot`/`delete_shot`/`reorder_shots` robust; ungültige scene_id→[].
- [ ] Implementierung `director.py`: `get_shots`, `save_shots`, `update_shot`,
      `delete_shot`, `_sanitize_shot` (prompt≤2000, shot-Key≤60, character_ids≤32,
      duration int 1..60, status in {planned,…}), `storage.shots_dir`.
- [ ] Commit: `feat(atelier/regie): shot storage + crud`

### Task 2: LLM-Zerlegung (`director.decompose_scene`)
- [ ] Test (LLM gemockt): `decompose_scene` baut Prompt aus Szene+Charakteren+CI,
      ruft `complete()`, parst JSON-Antwort robust (Markdown-Fences tolerant),
      erzeugt sanitized Shots mit status planned. Fehlerhafte LLM-Antwort → [].
- [ ] Implementierung: System-Prompt (Regisseur, gibt striktes JSON-Array),
      User-Prompt mit Szenen-Kontext; `_parse_shots_json` (fence-tolerant).
- [ ] Commit: `feat(atelier/regie): llm scene decomposition`

### Task 3: decompose-Route (ganzes Drehbuch, async Job)
- [ ] Test: POST decompose legt Job an (gemockt); GET job-status; Guard 404.
- [ ] Implementierung: `POST /screenplay/decompose` startet Hintergrund-Task
      (nutzt _jobstore-Muster), zerlegt alle Szenen der scene_order nacheinander,
      schreibt shots + Job-Fortschritt. `GET /screenplay/decompose/{job}`.
      Plus Shot-CRUD-Routen (GET/PUT/DELETE shots je Szene).
- [ ] Commit: `feat(atelier/regie): decompose route + shot crud routes`

## Akzeptanzkriterien
- [ ] User kann Drehbuch zerlegen lassen → je Szene ≥1 Shot mit Prompt+Kamera+Charakteren.
- [ ] Nichts wird generiert (kein Bild/Video-Call in Phase 1).
- [ ] Shots sind danach abrufbar/editierbar/löschbar; Guard greift.
- [ ] LLM-Fehler/kaputtes JSON crasht nicht — leere/teilweise Shot-Liste, Job „failed" mit Meldung.
- [ ] Tests grün (LLM gemockt), ruff clean, bestehende Tests unberührt.

## Nicht in diesem Plan
- Frontend-Storyboard-UI (eigener Schritt E4b, nach Backend).
- Batch-Render / echte Generierung (E5).
- Akt-Ebene (E3).
