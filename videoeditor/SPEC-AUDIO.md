# Video-Editor — Nachvertonung: Mehrspur-Audio + Audio-Editing (Spec)

Status: DESIGN (Brainstorming abgeschlossen 2026-07-02, freigegeben durch Till)
Baut auf: `SPEC.md` (Phase 1 Video-Schnitt, fertig) und `DEEPDIVE-CUTTOFFL.md` (Phase 2 Audiospur)
Ersetzt: die "Phase 2 — Audiospur (eine Spur)"-Skizze aus dem Deepdive durch ein
echtes Mehrspur-Modell mit Audio-Editing.

---

## Was

Der Video-Editor bekommt ein **Mini-Tonstudio in der Timeline**: mehrere
Audiospuren zusätzlich zum Original-Ton des Videos, auf denen generierte
Media-Files (Musik via `generate_music`, Sprache via `generate_speech`, sowie
`.wav`/`.mp3` aus dem Projekt-Workspace) platziert, getrimmt und gemischt werden.
Der Export mischt alle Spuren + O-Ton in **einem** ffmpeg-Schritt zusammen —
**kein Vormischen extern, kein Runter-/Hochladen.**

## Warum

Till will Videos nachvertonen (Musik unterlegen, Voiceover einsprechen lassen)
**ohne** ein zweites Werkzeug. Eine Einzel-Overlay-Spur (die Deepdive-Phase-2-
Skizze) würde erzwingen, Musik+Voice vorher woanders zu mischen — das wäre ein
Bruch im Workflow und unterm Strich mehr Arbeit pro Video. Mehrspur direkt im
Editor ist einmalig etwas mehr Bau-Aufwand, spart aber bei **jedem** Video das
Vormischen und den Datei-Ping-Pong. "Gleich richtig machen."

## Umfang: Mehrspur + Audio-Editing

**Spuren:**
- Original-Video-Ton als Spur 0 (aus dem Video, mute-bar, Gain regelbar).
- N zusätzliche Audiospuren (Musik, Voice, SFX — beliebig viele, Praxis 1–4).
- Pro Spur: Name, Mute, Solo, Master-Gain.

**Clips (pro Spur):**
- Import generierter/vorhandener Audiofiles aus dem Projekt-Workspace
  (`generated/*.mp3|wav` + überall im Workspace liegende Audiodateien),
  analog zum bestehenden Video-`/browse`+`/import`.
- Platzierung auf der Zeitachse: `t_start` (Timeline-Position) + `src_start`/
  `src_end` (Ausschnitt aus der Quelle) → Musik-Einsatz punktgenau, Voice an
  bestimmter Stelle.
- Trim per Drag (In/Out), Verschieben, Split am Playhead, Löschen.
- **Audio-Editing pro Clip:** Gain (dB), Fade-In, Fade-Out (Sekunden).
- **Crossfade** zwischen überlappenden Clips derselben Spur.

**Ausrichtung / UX:**
- Wellenform-Anzeige pro Audio-Clip (Peaks, serverseitig vorberechnet) zum
  optischen Ausrichten an Bild/Schnitt.
- Snap: Audio-Clip-Kanten snappen an Video-Schnittgrenzen und an den Playhead.

**Mix beim Export:**
- Ein ffmpeg-`-filter_complex`-Graph mischt alle aktiven Spuren + O-Ton:
  pro Clip `atrim`→`adelay`(t_start)→`volume`(gain)→`afade`(in/out),
  pro Spur `amix`/`concat`, final `amix` aller Spuren + `loudnorm` (EBU R128).
- Solo überschreibt Mute; gemutete/nicht-solo Spuren fallen aus dem Graph.

## Explizit NICHT (spätere Ausbaustufe)

- Automatisches **Ducking** (Musik leiser wenn Stimme spricht) — Phase 2b,
  `sidechaincompress`. Erst wenn manuelles Gain/Fade steht.
- Lautstärke-**Automation-Kurven** (Keyframe-Volumen über Zeit) — Phase 2b.
- Effekte (EQ, Hall, Kompressor global) — Phase 2c.
- Aufnahme direkt im Browser (Mikrofon) — separat.

## Bestehende Patterns (wiederverwendet)

- **Import:** `routes.py` `/browse` + `/import` (projekt-scoped, kein Silo) ist
  das exakte Muster. Audio-Browse = gleiche Idee für `.mp3/.wav/.m4a/.ogg`.
  Kein Kopieren nötig — Originale bleiben im Workspace, wir referenzieren
  `source_rel` (wie Video). Musicplayer-`import_routes.py` als Zweitreferenz.
- **ffmpeg:** `_ffmpeg.py` `run()` (async, Args-Liste, keine Shell). Neue
  Funktionen `audio_probe()`, `audio_peaks()`, und der Mix-Graph im Export.
- **EDL:** `models.py` wird um `AudioTrack`/`AudioClip` erweitert; EDL bekommt
  optionales Feld `audio: list[AudioTrack]` (rückwärtskompatibel — altes EDL
  ohne Audio bleibt gültig).
- **Export:** `export_service.py` erzeugt bereits das stumme Video per Concat.
  Neuer Schritt: aus dem Concat-Ergebnis + Audio-Graph das finale Mux. Falls
  keine Audiospuren definiert → Verhalten wie heute (O-Ton passthrough).
- **Jobs:** bestehendes Job-Pattern (`_jobstore.py`) für Peaks-Vorberechnung
  (async, wie Import/Export).

## Datenmodell (Erweiterung `models.py`)

```python
class AudioClip(BaseModel):
    id: str
    source_rel: str          # workspace-relativ (bleibt im Projekt)
    t_start: float = Field(ge=0)      # Position auf der Timeline (s)
    src_start: float = Field(ge=0)    # Ausschnitt-Anfang in der Quelle
    src_end: float = Field(gt=0)      # Ausschnitt-Ende in der Quelle
    gain_db: float = 0.0
    fade_in: float = Field(default=0.0, ge=0)
    fade_out: float = Field(default=0.0, ge=0)

class AudioTrack(BaseModel):
    id: str
    name: str = "Audio"
    mute: bool = False
    solo: bool = False
    gain_db: float = 0.0
    clips: list[AudioClip] = Field(default_factory=list)

# EDL erweitert:
#   original_audio: dict  -> {"mute": bool, "gain_db": float}
#   audio: list[AudioTrack]
```

Peaks werden NICHT im EDL gespeichert (host-spezifisch, groß) — separat als
Sidecar-JSON pro `source_rel`-Hash, live nachgeladen (wie Proxy/Sprite-Pfade).

## API (Erweiterung `routes.py`)

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/projects/{pid}/audio/browse` | Audiodateien im Projekt-Workspace (mp3/wav/m4a/ogg), mit `already_prepared`-Flag |
| POST | `/projects/{pid}/audio/prepare` | Peaks + Dauer vorberechnen (async Job), Body `{source_rel}` |
| GET | `/projects/{pid}/audio/{audio_id}` | Meta (duration, peaks_abs) für eine aufbereitete Audiodatei |
| GET | `/projects/{pid}/audio/{audio_id}/peaks` | Peaks-JSON (oder via `peaks_abs` + /api/files wie Proxy) |

EDL-Speichern läuft über den **bestehenden** `PUT …/edl` — `audio` ist Teil des
EDL-Bodys. Export über den **bestehenden** `POST …/export`.

Alle Endpunkte projekt-scoped via `_guard` (Projekt-Mitglied) — **kein**
Admin-only, da der Editor ohnehin projekt-scoped ist und aus dem eigenen
Workspace liest. (Damit ist die Zugangsfrage beantwortet: Editor-Zugang = Import.)

## ffmpeg — Mix-Graph (Kern)

Nach dem stummen Video-Concat (`video_only.mp4`) und mit Original-Ton
(`orig.m4a`, aus dem geschnittenen Video extrahiert respektive schon vorhanden):

Pro Audio-Clip `c` auf Eingang `[i]`:
```
[i]atrim=start=src_start:end=src_end,asetpts=PTS-STARTPTS,
   adelay={t_start*1000}|{t_start*1000},
   volume={gain_db}dB,
   afade=t=in:st=0:d={fade_in},
   afade=t=out:st={dur-fade_out}:d={fade_out}[a_c];
```
Pro Spur die Clips per `amix`/`concat` zu `[track_k]`, Spur-Gain via `volume`.
Final:
```
[track_0][track_1]...[a_orig] amix=inputs=N:normalize=0,
   loudnorm=I=-16:TP=-1.5:LRA=11 [aout]
```
Dann Mux: `-map 0:v -map "[aout]" -c:v copy -c:a aac`.

- Gemutete/nicht-solo Spuren + gemuteter O-Ton werden aus dem Graph gelassen.
- Keine Audiospuren definiert → alter Pfad (O-Ton passthrough, `-c copy`).
- Graph-Bau in eigener Datei `_audio_mix.py` (<200 Zeilen), von
  `export_service.py` aufgerufen.

## Frontend (eigene Umsetzung)

- Unter der Video-Timeline ein **Spuren-Stack**: pro Spur eine Zeile mit
  Header (Name, Mute/Solo/Gain) + Clip-Bereich mit Wellenform.
- Audio-Bibliothek-Panel: Browse generierter/vorhandener Files → per Drag/Klick
  auf eine Spur legen (an Playhead oder gesnappt).
- Clip-Inspector: Gain-Slider (dB), Fade-In/Out-Felder, Trim per Drag.
- Wiederverwendung des Canvas-Timeline-Renderings; Wellenform als eigener
  Draw-Helper (`_audioDraw.ts`), nicht in eine Riesendatei.
- Snap teilt sich die Logik mit dem Video-Keyframe-Snap.

## Akzeptanzkriterien

- [ ] Audio-`/browse` listet mp3/wav/m4a/ogg aus dem Projekt-Workspace inkl.
      generierter Files, mit `already_prepared`-Flag.
- [ ] `prepare` erzeugt Peaks + Dauer async (Job-Status pollbar); Wellenform
      erscheint im Editor.
- [ ] Mehrere Spuren anlegbar; Audio-Clips platzieren/trimmen/verschieben/
      splitten/löschen; EDL persistiert `audio`.
- [ ] Pro Clip Gain + Fade-In/Out wirken hörbar im Export.
- [ ] O-Ton mute + Spur-Mute/Solo wirken korrekt im Export.
- [ ] Crossfade zwischen zwei überlappenden Clips einer Spur klingt sauber.
- [ ] Export mischt alle aktiven Spuren + O-Ton, loudnorm-normalisiert, Video
      per `-c:v copy` (kein Bild-Reencode nur wegen Ton).
- [ ] EDL ohne `audio`-Feld exportiert exakt wie bisher (Rückwärtskompat).
- [ ] Kein `shell=True`; alle ffmpeg-Args als Liste. Dateien <200 Zeilen.
- [ ] Tests: AudioClip/Track-Validierung, Mix-Graph-String-Bau (ohne echten
      ffmpeg-Call, wie Video-Segment-Args getestet werden), Peaks-Job-Status.

## Offene Design-Punkte (bei Bau zu entscheiden, kein Blocker)

- Peaks-Auflösung/Format (Sample-Count pro Sekunde, Min/Max-Paare als
  Base64-Int16 vs. JSON-Array) — beim Bau von `audio_peaks()` festlegen.
- Original-Ton: on-the-fly aus dem geschnittenen Video ziehen vs. separat
  extrahieren — im Export-Refactor entscheiden.
- Crossfade-Umsetzung: `acrossfade` (nur benachbarte Paare) vs. manuelle
  afade-Überlappung im amix — Prototyp klärt, was sauberer klingt.
```
```

## Implementierungs-Reihenfolge (nach Freigabe)

1. Datenmodell (`models.py`) + EDL-Rückwärtskompat + Tests.
2. `audio_probe()` + `audio_peaks()` in `_ffmpeg.py`, `prepare`-Job, `/audio/*`-Routen.
3. `_audio_mix.py` (Graph-Bau) + Integration in `export_service.py`, Mix-Tests.
4. Frontend: Spuren-Stack, Wellenform-Render, Clip-Inspector, Audio-Bibliothek.
5. Crossfade + Solo/Mute-Feinschliff.
6. hh-review + Merge.
