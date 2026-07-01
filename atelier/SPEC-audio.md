# Atelier — Audio (Phase 1: Musik-Generierung)

## Ziel

Musik/Songs mit Serien-Konsistenz generieren — direkt im Atelier, im selben
Projekt-Kontext wie Bild/Video/Film. Grund: Musik ist **Zutat für die Filme**,
die das Atelier baut. `film.py` hat `music_rel` bereits vorbereitet, die
Film-Spec markiert Musik-Generierung explizit als offene Phase 2 — genau das
wird hier geschlossen.

## Warum im Atelier (nicht eigenes Modul)

Till: "Musik/Filmmusik/Effekte/Sprache für die Filmchen". Ein separates Modul
würde Assets zwischen zwei Projekten/Werkzeugen hin- und herkopieren müssen.
Im Atelier: ein Projekt-Kontext, eine Galerie, `music_rel` im Film-Schnitt
direkt aus der Audio-Bibliothek wählbar — reibungsloser Fluss Bild→Ton→Film.

## Scope dieser Runde: NUR Musik

Sprache (Stimmen-Profile) und Soundeffekte folgen als spätere, gleich
strukturierte Tabs im selben Audio-Bereich (Phase 2/3, separate Specs).

## Wiederverwendete Core-Bausteine (kein Rad neu erfinden)

`hydrahive.tools._openrouter_media`:
- `openrouter_key()` — zentraler Key-Lookup
- `read_audio_sse(resp)` → `(base64_parts, done)` — der geknackte SSE-Parser
  (Lyria liefert Audio als EINE mehrere-MB-Zeile; httpx' aiter_lines() zerlegt
  sie nicht-deterministisch, muss über rohe Bytes selbst getrennt werden)
- `save_bytes(raw, dest_dir, ext)` — Datei-Speicherung

`hydrahive.llm.media_models`:
- `get_media_model("music")` — aktives Default-Modell aus der Config
- Modelle: `google/lyria-3-pro-preview` (Stücke), `google/lyria-3-clip-preview` (Clips)

Request-Format (verifiziert, aus `generate_music.py` übernommen):
```
POST https://openrouter.ai/api/v1/chat/completions
{ model, messages:[{role:"user", content: prompt}],
  modalities: ["text","audio"], audio: {"format":"mp3"}, stream: true }
```

## Konsistenz-Hebel bei Musik (anders als Bild — ehrlich benannt)

Kein Referenzbild/Seed-Äquivalent (Lyria nimmt nur Text). Konsistenz läuft
rein über den Prompt:
- **CI-Kit-Erweiterung**: `music_style_anchor` — Studio-Sound (Genre, Mood,
  Instrumentierung, Tempo-Gefühl), der in jeden Musik-Prompt einfließt
- **Sound-Profile** (wiederverwendbare Track-Anker, analog zu Charakteren):
  Name, Beschreibung (Genre/Mood/Instrumente/BPM, verbatim in den Prompt),
  Ziel-Modell. KEIN Bild-Feld — eigenständiges Datenmodell, kein Zwang in
  `character.json` zu passen.

## Datenmodell (dateibasiert, wie der Rest des Moduls)

```
atelier/audio/
  <uuid>.mp3                 generierter Track
  <uuid>.mp3.json             Sidecar: {prompt, profile_ids, model, created_at}
  profiles/<id>/profile.json  Sound-Profil: {id, name, description, model}
ci.json (erweitert):
  + music_style_anchor: str
```

## Architektur

```
backend/
  audio_storage.py    audio_dir(), profiles_dir(), save_audio_bytes() — Pfade
                       (storage.py bleibt Bild/Video-fokussiert, hier eigene
                       Datei wg. 200-Zeilen-Grenze; nutzt dieselben Helfer-
                       Muster wie storage.py: safe_under, new_id, is_valid_id)
  audio_profiles.py   CRUD Sound-Profile (analog characters.py, schlanker)
  music.py            build_music_prompt() + generate_music() — eigener
                       SSE-Client (importiert read_audio_sse/openrouter_key
                       aus hydrahive.tools._openrouter_media)
  audio_routes.py      /api/modules/atelier/projects/{id}/audio/*
                       (eigener Router, wie media_routes.py für Video)
routes.py (minimal +): ci.json music_style_anchor durchreichen (CIIn erweitern)
```

## API

```
GET    /projects/{id}/audio/profiles          → [profile,...]
POST   /projects/{id}/audio/profiles          {name, description, model?}
PUT    /projects/{id}/audio/profiles/{pid}    → update
DELETE /projects/{id}/audio/profiles/{pid}
GET    /projects/{id}/audio/library           → [{rel, prompt, profile_ids, model, created_at}]
POST   /projects/{id}/audio/generate          {scene, profile_ids:[], model?}
                                               → {rel, prompt, model, created_at}
POST   /projects/{id}/audio/library/delete    {rel}
```

`scene`: das Variable ("treibender Retro-Synth-Loop für die Verfolgungsjagd").
Voller Prompt = `ci.music_style_anchor` + Profil-Beschreibungen (verbatim) + scene.

Generierung ist synchron (Lyria antwortet in ~10-30s, kein Job-Polling nötig
wie bei Video) — analog zum bestehenden Bild-Flow, nicht zum Video-Job-Muster.

## Frontend

```
frontend/
  AudioPanel.tsx        neuer Tab "Audio" (Projekt-Picker-Ebene wie Bild/Video)
  AudioProfiles.tsx      Sound-Profile anlegen/wählen (links, wie CharacterLibrary)
  AudioLibrary.tsx        generierte Tracks (Player pro Zeile: <audio controls>)
  api.ts + types.ts       ergänzen
index.tsx: AudioPanel als weiterer Tab in AtelierPage
```

Film-Integration: `FilmPanel.tsx` bekommt bei der Musik-Auswahl einen Link/
Button "aus Audio-Bibliothek wählen" statt nur freier Dateiname — schließt
die music_rel-Lücke aus SPEC-film.md.

## Akzeptanzkriterien

1. CI-Kit hat `music_style_anchor` (Studio-Sound), im Frontend editierbar.
2. Sound-Profil anlegen (Name, Beschreibung/Genre/Mood/BPM) — projektgebunden.
3. Musik generieren: CI-Anker + gewählte Profile (verbatim) + Szene → voller
   Prompt → Lyria → Track landet in `atelier/audio/` + Sidecar.
4. Bibliothek zeigt alle Tracks des Projekts, abspielbar, löschbar.
5. Track ist in `FilmPanel` als `music_rel`-Kandidat direkt wählbar.
6. Fehlerfall (Key fehlt, API-Fehler, leerer Stream) klar sichtbar, kein 500.
7. ruff/tsc/build grün, Backend-Tests grün, Dateien ≤200 Zeilen.

## Nicht in dieser Runde

- Sprache/Stimmen-Profile (Phase 2, eigene Spec).
- Soundeffekte/SFX-Bibliothek (Phase 3, eigene Spec).
- Musik-Editing (Trimmen, Loop-Punkte, Lautstärke) — nur generieren + ablegen.
- Weitere Musik-Modelle über Lyria hinaus (später, falls gewünscht).
