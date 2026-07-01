# Video-Editor-Modul — MVP-Spec

Status: DESIGN (freigegeben durch Till, 2026-07-02)
Inspiration (Konzept/Features, NICHT Code): github.com/HalloWelt42/CuttOffl
(Lizenz CC BY-NC-ND — daher komplett eigener Code, eigenes Aussehen).

## Was

Ein Web-Video-Schnittstudio als eigenständiges HH2-Modul (`videoeditor`):
Video hochladen → in einer Timeline mit Filmstrip-Thumbnails und Keyframe-
Anzeige schneiden → Export mit Hybrid-Rendering (verlustfreies Kopieren wo
möglich, Neu-Encoding nur wo nötig).

## Warum

Till möchte die Editor-**Features** von CuttOffl (Timeline-UX, Keyframe-Magnet,
Hybrid-Export) in HH2 verfügbar haben — als eigenständiges, selbst gebautes
Modul. Kein Codekopieren (Lizenz verbietet Weiterverbreitung modifizierter
Versionen), nur Konzept-Übernahme + eigene Umsetzung in unserem React/FastAPI-
Stack.

## Bestehende Patterns (wiederverwendet)

- Modul-Struktur wie `atelier/`: `manifest.json`, `backend/`, `frontend/`,
  `tests/`
- `atelier/backend/_ffmpeg.py`-Muster: `asyncio.create_subprocess_exec` mit
  Args-Liste (keine Shell-Injection), `ffprobe` für Metadaten — gleicher Stil,
  eigene Datei `videoeditor/backend/_ffmpeg.py`
- Job-Pattern: eigener `_jobstore.py` analog Atelier (Render-Jobs mit Status/
  Progress, wie Atelier es für Video-Generierung schon hat)

## MVP-Umfang (Phase 1 — dieser Sprint)

**Backend:**
- Upload-Endpoint (Original + async Proxy-Erzeugung, 480p H.264)
- Keyframe-Extraktion via `ffprobe` (Zeitstempel-Liste)
- Sprite-/Thumbnail-Strip-Erzeugung für den Filmstreifen (analog Atelier-
  Thumbnails, aber Zeitraster statt Einzelbild)
- EDL-Datenmodell: Liste von Clips `{src_start, src_end, mode: copy|reencode}`,
  persistiert als JSON (SQLite via bestehende Core-DB-Anbindung, kein neues
  DB-System)
- Export-Job: pro Segment entscheiden copy (stream-copy an Keyframe-Grenzen)
  vs. reencode (frame-genauer Schnitt) — Konkatenation via FFmpeg concat-Demuxer
- Job-Progress via bestehendem Modul-Job-Pattern (Polling, wie Atelier)

**Frontend (eigene Umsetzung, eigenes Aussehen):**
- Upload + Bibliotheks-Ansicht (Kacheln, wie Atelier-Gallery als Vorbild)
- Editor-Seite: Video-Player oben, Canvas-Timeline unten
  - Timeline-Bänder (von oben nach unten): Zeit-Lineal, Keyframe-Marker,
    Filmstrip-Thumbnails, Clip-Bereich (copy=grün/reencode=lila wie Konzept,
    eigene Farbwahl)
  - Zoom (Mausrad+Strg), horizontales Scrollen, Playhead mit Snap-zu-Keyframe
  - Schnitt: In/Out per Taste, Split am Playhead, Clip-Kanten per Drag trimmen
  - Auto-Follow der Timeline während der Wiedergabe (sanftes Nachziehen)
- Export-Dialog: Auflösung/Codec-Presets (Hardware-Erkennung: nutzt bestehende
  Atelier-Hardware-Checks falls vorhanden, sonst eigener `hwaccel_service`-
  artiger Check)

## Explizit NICHT in Phase 1 (spätere Phasen)

- **Phase 2**: Audiospur (separate Zeile, eigene Clips, Wellenform-Anzeige,
  Gain/Mute, Audio-Mix-Export)
- **Phase 3**: Lokale KI-Untertitel (Whisper), SRT/VTT-Export
- Bibliotheks-Ordnerstruktur/Tags (Phase 1: flache Liste reicht)
- Mehrspur-Video (nur eine Video-Spur in Phase 1)

## Technische Eckpunkte

- FFmpeg-Aufrufe ausschließlich über `asyncio.create_subprocess_exec` mit
  Args-Liste — niemals `shell=True` (Security).
- Hardware-Encoder-Erkennung analog Konzept (VideoToolbox/NVENC/VAAPI/
  libx264-Fallback) — eigene Implementierung.
- EDL als einfaches JSON-Schema, kein externes EDL-Format nötig.
- Max ~200 Zeilen/Datei — Timeline-Rendering (Canvas-Draw-Funktionen) auf
  mehrere Dateien aufteilen (z.B. `TimelineCanvas.tsx` + `_timelineDraw.ts`
  Helper-Modul), nicht eine große Datei wie im Vorbild.

## Akzeptanzkriterien (Phase 1)

- [ ] Video-Upload erzeugt Original + 480p-Proxy asynchron
- [ ] Timeline zeigt Filmstrip-Thumbnails + Keyframe-Marker korrekt zur Zeit-
      Achse ausgerichtet
- [ ] Schnitt (In/Out/Split/Trim) funktioniert, EDL wird persistiert
- [ ] Export erzeugt korrektes Video; copy-Segmente sind verlustfrei/schnell,
      reencode-Segmente frame-genau
- [ ] Kein Code aus CuttOffl übernommen (Diff-Review vor Merge)
- [ ] Tests: EDL-Validierung, ffmpeg-Kommando-Konstruktion (ohne echten
      ffmpeg-Call testbar, wie Atelier es macht), Job-Status-Übergänge

## Offene Punkte für Phase 2/3
- Whisper-Engine-Wahl (mlx-whisper/faster-whisper) — erst wenn Phase 3 ansteht
- Audio-Wellenform-Rendering-Ansatz (Canvas vs. SVG) — bei Phase 2 entscheiden
