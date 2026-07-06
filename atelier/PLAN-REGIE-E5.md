# Plan: Regie E5 — Batch-Render (freigegebene Shots → fertiger Film)

## Ziel
Nach E5 kann der User die vom Regieagenten erzeugten (und geprüften) Shots per
**„Freigeben & generieren"** tatsächlich rendern lassen: pro Shot ein Keyframe-
Bild (mit Charakter-Referenzen) → daraus ein Video-Clip → am Ende alle Clips zu
einem Film zusammenschneiden. Fortschritt je Shot ist live sichtbar.

## Bestehende Bausteine (Wiederverwendung, kein Neubau)
- `service.generate_for_project(pid, req)` — Keyframe-Bild (sync), nutzt Charakter-
  Referenzen + CI + Kamera. Gibt `{rel, ...}` zurück.
- `video.py` submit/poll/download — bereits vorhanden, aber nur als Job-Runner.
  → NEU: `render_clip()` als await-bare Funktion (submit→poll→download, ohne Job-Datei).
- `film.start_film_job(pid, {clips, resolution, music_rel})` — Zusammenschnitt.
- `director.py` (E4) — Shots mit status planned/…; `get_shots`, `save_shots`.
- `_jobstore` — Render-Job-Status (Fortschritt).

## Ablauf pro Shot (sequenziell je Szene)
1. status `planned` → Keyframe via `generate_for_project`
   (scene=shot.prompt, character_ids=shot.character_ids, camera aus shot.shot).
   → `image_rel` in Shot speichern, status `image_ready`.
2. status → `video_processing`: `render_clip(source_rel=image_rel, prompt=shot.prompt,
   model=film_model, duration=shot.duration, aspect=head.aspect_ratio)`.
   → `video_rel` in Shot, status `done`.
3. Fehler → status `failed` + Fehlermeldung im Shot (Batch läuft weiter).
Am Ende: alle done-Clips (in Szenen-/Shot-Reihenfolge) → `film.start_film_job`.

## Datenmodell — Render-Job
```
atelier/screenplay/render.json   # ein aktiver Render-Job je Projekt
  { job_id, status: pending|processing|completed|failed,
    total_shots, done_shots, failed_shots,
    current: "<scene-title> / shot #n", film_rel, error, created_at }
```

## Implementierungsreihenfolge (TDD)

### Task 1: `video.render_clip()` (await-bar, ohne Job-Datei)
- [ ] Test (submit/poll/download gemockt): gibt videos/-rel zurück; Fehler propagiert.
- [ ] Implementierung: extrahiert die submit→poll→download-Kette aus `_run_job`
      in eine wiederverwendbare `render_clip(project_id, *, source_rel, prompt,
      model, duration, aspect_ratio) -> str` (rel). `_run_job` nutzt sie danach auch.
- [ ] Commit: `refactor(atelier/video): render_clip als await-bare Funktion`

### Task 2: `director.render_all()` (Orchestrator)
- [ ] Test (generate_for_project + render_clip + film gemockt): iteriert Shots
      aller Szenen, setzt Status planned→image_ready→video_processing→done,
      schreibt image_rel/video_rel, ruft am Ende Film-Merge; Shot-Fehler → failed,
      Batch läuft weiter; Render-Job-Status stimmt (total/done/failed).
- [ ] Implementierung: `render_all(pid, *, model)` + Render-Job-Persistenz
      (`get_render_job`/`_write_render_job`).
- [ ] Commit: `feat(atelier/regie): batch-render orchestrator`

### Task 3: Routen
- [ ] Test: POST render startet (gemockt, non-blocking via create_task); GET status; Guard.
- [ ] Implementierung: `POST /screenplay/render` (startet Hintergrund-Task),
      `GET /screenplay/render` (Job-Status).
- [ ] Commit: `feat(atelier/regie): render route + status`

### Task 4: Frontend
- [ ] „Freigeben & generieren"-Button (nur wenn ≥1 Shot planned).
- [ ] Fortschritts-Anzeige (pollt render-status): total/done/failed, current.
- [ ] Shot-Status-Badges im Storyboard (planned/image_ready/…/done/failed).
- [ ] Commit: `feat(atelier/regie): render UI + progress`

## Akzeptanzkriterien
- [ ] „Freigeben & generieren" erzeugt je Shot Keyframe→Clip, dann einen Film.
- [ ] Nutzt ausschließlich vorhandene generate/video/film-Pfade (Referenzen greifen!).
- [ ] Fortschritt live; ein fehlgeschlagener Shot bricht den Batch nicht ab.
- [ ] Tests grün (alles gemockt — kein echter API-Call), ruff clean, tsc grün.

## Nicht in diesem Plan
- Continue-Frame-Verkettung *innerhalb* einer Szene (später; v1 = eigenständige Clips).
- Dialog-Voiceover/Untertitel (E6). Akt-Ebene (E3).
- Paralleles Rendern mehrerer Shots (v1 sequenziell — einfacher, schont Rate-Limits).
