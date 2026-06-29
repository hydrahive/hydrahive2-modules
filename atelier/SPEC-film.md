# Atelier — Film-Schnitt (Phase 1: Clips zusammenfügen + Musik)

## Ziel

Mehrere fertige Video-Clips (aus der Galerie) in einer Reihenfolge zu einem
Film zusammenfügen, optional mit Musik unterlegt. Lokal via ffmpeg — kostet
keine API-Credits.

## Verifizierte Fakten (real getestet 2026-06-30)

- ffmpeg 6.1.1 mit concat, xfade, afade, amix, libx264, aac — alles da.
- Clips haben GEMISCHTE Auflösungen (1280x720, 1366x768, 768x1344 hochkant!).
  → simples concat reicht NICHT, jeder Clip muss auf ein Zielformat
  normalisiert werden (scale + pad + setsar + fps).
- Verifizierte Pipeline (2 Clips gemischter Auflösung → 1280x720): 0,7s.
- Musik drunter + afade-out + -shortest: 0,18s. Ergebnis hat video+audio.

## Pipeline (Kern)

Pro Clip: `scale=W:H:force_original_aspect_ratio=decrease,
pad=W:H:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24` → alle gleich groß (Letterbox
für abweichende Seitenverhältnisse, nichts verzerrt). Dann `concat=n=N:v=1:a=0`.
Optional Musik: zweiter Input, `afade=t=out`, `-map`, `-shortest`.

## Async-Job (wie Video)

Rendern dauert nur Sekunden, aber wir bleiben beim bewährten async-Job-Muster
(nicht den Request blockieren). Dateibasierter Job-Store wie bei Video.

## Backend

```
backend/film.py     # render_film(project_id, req) async:
                    #   ffmpeg-Kommando bauen (Normalisierung + concat + Musik),
                    #   subprocess, Ergebnis nach films/<uuid>.mp4, Job-JSON.
                    #   list_film_jobs(). Job-Store: atelier/films/<job>.json
storage.py +: films_dir()
routes.py +:
  GET  /projects/{id}/films          → Job-Liste
  POST /projects/{id}/films          {clips:[rel,...], resolution?, music_rel?}
```

Auflösung: Default 1280x720 (16:9). Clips = Liste der video_rel aus der Galerie
(Reihenfolge = Film-Reihenfolge). music_rel optional (eine vorhandene Audiodatei
im Projekt; Musik-GENERIEREN kommt als Phase 2).

Sicherheit: alle rel-Pfade über storage.safe_under validieren (kein Traversal).
ffmpeg-Argumente als Liste (kein shell=True) → keine Injection.

## Frontend

- Neue Sektion unter dem VideoPanel: "🎞️ Film schneiden".
- Liste der fertigen Clips (aus VideoPanel-Daten) mit Checkbox/Reihenfolge:
  v1 simpel — Clips anklicken in Wunsch-Reihenfolge (nummeriert), kein
  Drag&Drop (das wäre Phase 2).
- Optional: Musik-Datei wählen (vorhandene im Projekt) — v1 evtl. weglassen
  wenn keine da, erst "ohne Musik" solide.
- "Film rendern" → Job startet → Polling wie Video → fertiger Film als
  <video> in der Film-Sektion.

## Phasen

- **Phase 1 (jetzt):** Clips in Reihenfolge + normalisieren + concat + rendern.
  Musik nur wenn eine Audiodatei existiert (sonst ohne).
- **Phase 2:** Crossfade-Übergänge (xfade), Drag&Drop-Reihenfolge, Clips
  trimmen, Musik per Lyria generieren.

## Akzeptanz

1. Mehrere Clips wählen (Reihenfolge) → "rendern" → Job startet, Request kehrt
   sofort zurück.
2. Gemischte Auflösungen werden sauber letterboxed (nichts verzerrt/abgeschnitten).
3. Fertiger Film spielt in der Film-Sektion, liegt in atelier/films/.
4. Fehlerfall (ffmpeg-Error) als "failed" sichtbar, kein 500.
5. ruff/tsc/build grün, Dateien <200 Zeilen, ffmpeg ohne shell=True.
