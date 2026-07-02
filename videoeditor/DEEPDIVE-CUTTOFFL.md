# Deep-Dive: CuttOffl-Schnittfeatures vs. unser videoeditor (Stand 2026-07-02)

Analyse der CuttOffl-Quellen (editor.svelte.js, render_service.py,
render_analysis.py, render_presets.py, Player.svelte, Timeline.svelte,
AudioTrack.svelte) — als Feature-Roadmap. NUR Konzept-Referenz, kein Code
übernommen (CuttOffl ist CC BY-NC-ND).

## Legende
✅ haben wir · 🟡 teilweise · ❌ fehlt

---

## 1. Schnitt & Timeline

| Feature | Status | Anmerkung |
|---|---|---|
| Keyframe-Extraktion (ffprobe) | ✅ | haben wir |
| Filmstrip-Thumbnails (Sprite) | ✅ | haben wir |
| Timeline-Canvas (Ruler/KF/Film/Clips) | ✅ | haben wir |
| In/Out, Split, Trim-Drag | ✅ | haben wir |
| **Keyframe-Magnet (Snap beim Schneiden)** | ❌ | CuttOffl: `snapTime()` zieht Schnitt auf nächsten Keyframe; Toggle `snapOn`. Wir snappen NICHT — Clip startet exakt wo geklickt → landet fast immer auf reencode |
| **copy/reencode LIVE pro Clip angezeigt** | 🟡 | wir färben Clips, aber ohne Live-Analyse *warum* |
| **Undo/Redo** | ❌ | CuttOffl: `history[]`/`future[]`, 80 Schritte. Wir: nichts |
| **Auto-Save (debounced 600ms)** | 🟡 | wir speichern nur auf Klick |
| **Snap-zu-Keyframe Sprünge (prev/next)** | ❌ | `jumpToPrevKeyframe`/`jumpToNextKeyframe` |
| **Zoom-Presets** (Übersicht…Frame-genau) | ❌ | wir haben nur Strg+Mausrad-Zoom |
| **Auto-Follow beim Abspielen** | 🟡 | wir haben Playhead, aber kein sanftes Mitlaufen der Timeline |
| **Smoothe Playhead-Nadel (rAF, 60fps)** | ❌ | CuttOffl liest currentTime per requestAnimationFrame statt nur timeupdate (~200ms) |

## 2. Preview / Playback

| Feature | Status | Anmerkung |
|---|---|---|
| Video-Player (Proxy) | ✅ | haben wir |
| Play/Pause, Leertaste | ✅ | haben wir |
| **Frame-Schritt (Pfeil ← →), ±10s (J/L)** | ❌ | `stepFrame`, `nudge` |
| **Vorschau: nur Auswahl-Bereich** | ❌ | `startRangePreview` |
| **Vorschau: einzelner Clip** | ❌ | `startClipPreview` |
| **Vorschau: ganze EDL zusammenhängend** | ❌ | `startTimelinePreview` — springt Clip für Clip, zeigt den SCHNITT wie er final aussieht, OHNE Rendern! Das ist DAS Kern-Feature zum Beurteilen |
| **Vollbild-Wiedergabe** | ❌ | |

## 3. Hybrid-Render (der Kern-Vorteil)

| Feature | Status | Anmerkung |
|---|---|---|
| copy vs reencode pro Segment | ✅ | haben wir (resolve_modes) |
| Keyframe-genaues copy / frame-genaues reencode | ✅ | haben wir |
| concat-Demuxer zum Zusammenfügen | ✅ | haben wir |
| **Output-Profile (Codec/Auflösung/Bitrate/CRF)** | ❌ | wir rendern immer Default h264. CuttOffl: OutputProfile mit codec/resolution/bitrate/crf/container |
| **profile_forces_reencode-Logik** | ❌ | wenn Ziel-Profil Skalierung/Codec-Wechsel fordert → ALLE Clips reencode (homogene Streams für concat). Wir haben das nicht, weil wir keine Profile haben |
| **HW-Encoder-Erkennung (VideoToolbox/V4L2/NVENC)** | ❌ | CuttOffl: `detect_hw_encoder`, `_hw_decode_flags` — Faktor 5-20 schneller bei 4K HEVC |
| **HW-Decode-Flags vor -i** | ❌ | |
| **Live-Render-Fortschritt (ffmpeg -progress)** | 🟡 | wir pollen nur Job-Status, kein %-Fortschritt aus ffmpeg |
| **Render-Presets (YouTube/Reel/Archiv/Nur-schneiden…)** | ❌ | 9 fertige Presets |
| **Größen-Schätzung vor Export** | ❌ | analyze_output schätzt Ausgabe-Bytes |
| **Einzel-Clip-Render** | ❌ | startRender(clipId) rendert nur einen Clip |

## 4. Audiospur (Phase 2)

| Feature | Status |
|---|---|
| Audio-Wellenform (Peaks) | ❌ |
| Audio-Track-Zeile (separate Clips) | ❌ |
| Gain/Fade-In/Out pro Clip | ❌ |
| Original-Ton stumm / Audio-Mix | ❌ |
| loudnorm (EBU R128) / Mono-Downmix | ❌ |

## 5. Untertitel (Phase 3)

| Feature | Status |
|---|---|
| Whisper-Transkription (lokal) | ❌ |
| Live-Segmente während Transkription | ❌ |
| SRT/VTT-Export mit EDL-Zeitmapping | ❌ |
| Untertitel-Overlay im Player | ❌ |

## 6. Bibliothek

| Feature | Status | Anmerkung |
|---|---|---|
| Videos aus Projekt-Workspace | ✅ | haben wir (kein Silo) |
| Virtuelle Ordner / Tags / Filter / Suche | ❌ | für uns wohl unnötig — Samba+Projekt-Workspace deckt das ab |

---

## Priorisierte Roadmap (Vorschlag)

**Phase 1.5 — „Schnitt richtig gut machen" (das fehlt am dringendsten):**
1. **Keyframe-Magnet / Snap** — ohne das ist jeder Schnitt reencode. Kern.
2. **Undo/Redo + Auto-Save** — Grund-Editor-Ergonomie
3. **Timeline-Vorschau (ganze EDL zusammenhängend abspielen)** — den Schnitt
   beurteilen OHNE Export. Das ist der „aha, so wird's"-Moment
4. **Frame-Schritt + Snap-Sprünge (Tasten)** — Präzision
5. **Render-Presets + Output-Profile** — „Nur schneiden" (passthrough,
   sekundenschnell) vs. YouTube/Web/Archiv
6. **Live-Render-Fortschritt (%)** — ffmpeg -progress auswerten
7. **HW-Encoder-Erkennung** — Speed bei großem Material

**Phase 2 — Audiospur** (Wellenform, Gain, Mix)

**Phase 3 — Whisper-Untertitel**

## Wichtigste Einzel-Erkenntnis
Der **Keyframe-Snap** (`snapOn` + `snapTime`) ist der Grund, warum CuttOffl
„so viel wie möglich kopiert": schneidet man snap-gezogen zwischen zwei
Keyframes, bleibt der Clip `copy` = bit-identisch, sekundenschnell. Ohne Snap
(unser Stand) landet fast jeder Schnitt auf `reencode`. Das ist der größte
Qualitäts-/Speed-Hebel und sollte als Erstes kommen.
