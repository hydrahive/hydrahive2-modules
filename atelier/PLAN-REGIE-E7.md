# Plan: Regie E7 — Szenen-Musik im Regie-Film (Original-Ton + Musik-Unterlegung)

## Ziel
Nach E7 hat der gerenderte Regie-Film **Ton**: Der Original-Ton der Clips
(Dialoge/Effekte aus dem Video-Modell) bleibt erhalten, und wo eine Szene
`music.enabled` hat, wird deren generierte Musik **zeitversetzt an der Position
dieser Szene leise druntergemischt** (Ducking-frei, feste Lautstärke).

Bisher: `render_all` ruft `film.start_film_job(..., music_rel="")` → Film ist
stumm bzw. hat nur Clip-Ton, Szenen-Musik wird komplett ignoriert.

## Problem-Fakten (frisch geprüft)
- Szene trägt `music = {enabled, prompt, music_rel}` — im UI aktuell nur
  `enabled` + `prompt` (Text), **kein music_rel** und **keine Generierung**.
- `music.generate_for_project(pid, {scene, model})` existiert → liefert
  `{rel: "audio/<name>.mp3", ...}`. Wird für die Szenen-Musik wiederverwendet.
- `film.build_concat_command` kann Musik nur als EINE durchgehende Spur, die den
  Clip-Ton ERSETZT. Für E7 (Ton behalten + mehrere Musikstücke zeitversetzt)
  reicht das nicht → neue, eigene Mux-Funktion im director-Kontext.
- ffmpeg 6.1.1 vorhanden → `amix` mit `weights` + `normalize=0`, `adelay`,
  `apad`, `volume` verfügbar.

## Nicht in E7 (bewusst)
- Kein Beat-/Takt-Sync, kein automatisches Ducking (sidechaincompress).
- Keine Crossfades zwischen Szenen-Musikstücken (harte Platzierung, apad).
- Musik-Auswahl aus Bibliothek (statt Generierung) — optionaler Nachschlag.

## Datenmodell
Szene `music.music_rel` wird endlich befüllt: Beim Render generiert der
Director pro `music.enabled`-Szene ein Musikstück (falls noch keins) und
speichert dessen rel im Shot-freien Szenen-Kontext (render.json-Zwischenstand,
NICHT die Szene selbst überschreiben — Szene bleibt Nutzer-Eingabe).

Der Film-Mux bekommt eine Liste `(clip_index_start, music_path)` bzw. einfacher:
`segments = [{start_sec, music_path}]`, wobei `start_sec` = Summe der Dauern
aller Clips vor der ersten Shot-Position dieser Szene.

## Ablauf render_all (erweitert)
1. Wie bisher: pro Shot Keyframe → Clip. Zusätzlich pro Clip die **echte Dauer**
   merken (ffprobe), um Szenen-Startzeiten auf der Film-Timeline zu berechnen.
2. Clips bleiben nach Szenen gruppiert → `scene_spans = [{scene_id, t_start, clips[]}]`.
3. Für jede Szene mit `music.enabled`:
   - `music_rel` = `music.generate_for_project(pid, {scene: music.prompt || scene.description, model: head.audio_model})`.
   - Fehler bei Musik = nicht-fatal (Film ohne diese Musik, Warnung in render.json).
4. Neuer Mux (`_director_mux.py`):
   - Video: alle Clips concat (nur Video, wie gehabt).
   - Audio: Clip-Original-Ton concat (mit Stille für tonlose Clips) = Basis-Spur A0.
   - Pro Szenen-Musik: `[music]adelay=t_start|t_start, apad, atrim=0:film_dauer, volume=MUSIC_GAIN[mN]`.
   - `amix=inputs=1+M:weights=1 …:normalize=0` → gemischte Spur.
   - Final: `-map [v] -map [amix] -c:v libx264 -c:a aac`.
5. Ergebnis als `films/<id>.mp4` (wie film-Job), rel in render.json.

Konstante: `MUSIC_GAIN = 0.35` (Musik ~ -9 dB unter Original). Später konfigurierbar.

## Dateien
- `backend/_director_mux.py` — NEU (<200 Z.): build_director_mux_command(clips, clip_durations, scene_music, out, w, h, gain) → ffmpeg-args. Reine Arg-Bauerei, testbar ohne ffmpeg.
- `backend/director.py` — render_all: Clip-Dauern sammeln, Szenen-Musik generieren, Mux statt film.start_film_job.
- `backend/_ffmpeg.py` — evtl. probe_duration-Helper (falls nicht vorhanden).
- `frontend/DirectorPanel.tsx` — Szenen-Musik-Hinweis: "Musik wird beim Rendern erzeugt und unter die Szene gelegt" (Text reicht; music_rel-Auswahl optional später).
- `atelier/manifest.json` — version bump.
- Tests: `tests/test_director_mux.py` — Arg-String-Bau (adelay je Szene, amix normalize=0, gain), Randfälle (keine Musik → Original-Ton-Pfad).

## Akzeptanzkriterien
- [ ] Regie-Film enthält Original-Clip-Ton (Dialog/Effekte hörbar).
- [ ] Szene mit music.enabled → deren Musik liegt ab der Szenen-Startzeit drunter, leiser als der Clip-Ton.
- [ ] Szene ohne Musik → nur Original-Ton in diesem Abschnitt.
- [ ] Musik-Generierungsfehler bricht den Film-Render NICHT ab (Film ohne diese Musik + Warnung).
- [ ] Kein music.enabled irgendwo → Film = reiner Clip-Ton-Concat (bestehender Pfad, kein amix).
- [ ] Tests grün, npm build grün, manifest version bump.

## Implementierungsreihenfolge (TDD)
1. `_director_mux.py` + `test_director_mux.py` (Arg-Bau, rein) — RED→GREEN.
2. `_ffmpeg.probe_duration` (falls fehlt) — kleiner Helper + Test.
3. `render_all` verdrahten (Dauern, Szenen-Musik, Mux) — bestehende Director-Tests grün halten.
4. Frontend-Hinweistext + i18n.
5. Build, hh-review, version bump, commit/push, hub-refresh.
