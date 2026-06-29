# Atelier — Video (Phase 1: Bild → Video)

## Ziel

Aus einem fertigen Galerie-Bild ein kurzes Video machen (Image-to-Video). Der
Startframe ist unser eigenes, konsistentes Bild → die Figur bleibt erhalten.
Das ist der natürlichste Einstieg und nutzt maximal, was schon da ist.

## Warum Image-to-Video zuerst

- Konsistenz "gratis": das Video startet aus dem generierten Bild (Figur/CI bleibt).
- Kling & Hailuo können image_url als Startframe (Core-Tool bestätigt).
- Text-to-Video von Null kommt später (Phase 2).

## Wiederverwendete Core-Bausteine (kein Rad neu erfinden)

`hydrahive.tools._openrouter_video`:
- `submit_video_job(prompt, model, *, key, width, height, duration, aspect_ratio, image_url)` → job_id
- `poll_video_job(job_id, *, key)` → {status, url, error}
- `download_video(url, dest_dir, *, key)` → Path (.mp4)

## Async-Job-Muster (Blaupause: deepresearch)

Video dauert 30-90s → NICHT im Request blockieren. Muster:
1. `POST /projects/{id}/videos` legt Job an (status=pending), startet
   `asyncio.create_task(_run_job(...))`, gibt sofort job-id zurück.
2. Hintergrund-Task: submit → poll-Schleife (alle ~5s) → download → Sidecar.
   Schreibt Status pending→processing→completed/failed in eine Job-Datei.
3. Frontend pollt `GET /projects/{id}/videos` (Liste mit Status) bis fertig.

State dateibasiert (wie der Rest des Moduls): `atelier/videos/<job>.json`
(status, source_rel, prompt, model, duration, video_rel?, error?, created_at)
+ das fertige `videos/<uuid>.mp4`.

## Backend

```
backend/video.py        # Job-Logik: start_video_job + _run_job (async),
                        #   list_video_jobs, dateibasierter Job-Store
routes.py +:
  POST /projects/{id}/videos     {source_rel, prompt, model?, duration?, aspect_ratio?}
  GET  /projects/{id}/videos     → [{job_id, status, video_rel?, source_rel, ...}]
storage.py +: videos_dir(), save_video_bytes()
```

Modelle: kling/kling-video-v2-master (default), minimax/hailuo-2.3 (beide I2V).
Key: `openrouter_key()` (zentrale Config, wie beim Bild).

## Frontend

- Galerie-Item bekommt Button "🎬 zu Video" → kleiner Dialog: Bewegungs-Prompt
  ("Kamera fährt langsam ran"), Dauer (5s), Modell.
- Neue Sektion/Tab "Videos" in der Galerie-Spalte: zeigt laufende Jobs
  (Spinner + Status) und fertige Videos (`<video controls>`).
- Polling: solange ein Job pending/processing ist, alle ~5s `videos` neu laden.
- Kosten-Hinweis im Dialog (Video ist teurer als Bild).

## Akzeptanz

1. Bild aus Galerie → "zu Video" → Job startet, Request kehrt sofort zurück.
2. "Video wird erstellt…" mit Status sichtbar; UI blockiert nicht.
3. Fertiges Video spielt in der Galerie (`<video>`), liegt in atelier/videos/.
4. Fehlerfall (API/Timeout) sichtbar als "fehlgeschlagen", kein 500.
5. Konsistenz: Video startet aus dem gewählten Bild (Startframe).
6. ruff/tsc/build grün, Dateien <200 Zeilen.

## NICHT in Phase 1

- Text-to-Video von Null (Phase 2).
- Clips aneinanderhängen / Schnitt (Phase 3).
- Vertonung.
