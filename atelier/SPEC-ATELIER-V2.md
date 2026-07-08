# Atelier v2 — Komplette Überarbeitung (UX, Struktur, Features)

> **Status: Design / Planung** — noch nichts implementiert.
> Entstanden 2026-07-08 aus Tills Feedback-Session.

---

## 1. Problem

Das aktuelle Atelier hat ein starres 3-Spalten-Layout (Charaktere links / Tabs
mitte / Filmschnitt rechts). Die Breite jeder Spalte ist fix, der Nutzer kann
nichts aus-/einblenden. Bei mehr als ~20 Bildern oder Videos wird die Galerie
unbrauchbar (2-Spalten-Vollbilder, ewiges Scrollen). Videos werden als volle
Player dargestellt statt als Thumbnails. Der Videoschnitt lebt in einem
separaten Modul, ohne Zugriff auf die von Atelier generierten Dateien. Datei-
namen sind reine UUIDs ohne Kontext (wann, was, welches Modell). Es gibt keine
einheitliche Onboarding-Hilfe pro Tab.

---

## 2. Ziele

1. **100 % Bildschirmbreite** — alle Funktionen in Tabs, keine fixen Seitenspalten.
2. **Galerie**: kompaktes Thumbnail-Grid (250 px / ~5 vw), Zoom per Klick.
3. **Videos**: Thumbnail-Vorschau (Loop-Preview), Overlay-Player bei Klick.
4. **Videoschnitt** als nativer Tab im Atelier (kein separates Modul mehr nötig),
   greift auf die Atelier-Projektdateien zu.
5. **Bessere Datei-Ablage** im Workspace: sprechende Dateinamen + Ordner nach
   Typ/Datum; UUID-Chaos beenden.
6. **Tab-Beschreibungen / Onboarding** — jeder Tab erklärt sich selbst.

---

## 3. Neues Tab-Layout

Alle Tabs in einer Leiste unter dem Header. Kein 3-Spalten-Grid mehr.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🎨 Atelier         [Projekt: MyFilm ▾]                   [? Hilfe]    │
├─────────────────────────────────────────────────────────────────────────┤
│  👥 Charaktere │ ✨ Generieren │ 🖼️ Galerie │ 🎬 Videos │ 🎵 Audio │   │
│  🎞️ Filme      │ ✂️ Schnitt    │ 🎬 Regie                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                        [aktiver Tab — volle Breite]                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Tabs (8 Stück, Reihenfolge nach Workflow):**

| # | Tab | Icon | Inhalt | Aktuell |
|---|---|---|---|---|
| 1 | Charaktere | 👥 | Charakter-Bibliothek (bisher linke Spalte) | CharacterLibrary |
| 2 | Generieren | ✨ | Bild-Generator + CI | GeneratePanel |
| 3 | Galerie | 🖼️ | Kompaktes Bild-Grid, Zoom, Promote, Video-Start | Gallery (neu) |
| 4 | Videos | 🎬 | Thumbnail-Grid generierter Clips, Overlay-Player | VideoPanel (neu) |
| 5 | Audio | 🎵 | Musik/TTS Generator + Audio-Bibliothek | AudioPanel |
| 6 | Filme | 🎞️ | Film-Zusammenschnitt (bisher rechte Spalte) | FilmPanel |
| 7 | Schnitt | ✂️ | Video-Editor (aus videoeditor-Modul) | VideoEditorPage (integriert) |
| 8 | Regie | 🎬 | Drehbuch, Regieagent, Batch-Render | ScreenplayPanel |

### Tab-Beschreibungen (Onboarding-Banner)

Jeder Tab zeigt beim ersten Aufruf (oder per "?" Collapse-Toggle) einen
2-Zeiler was dieser Tab macht und wie man anfängt:

```
👥 Charaktere — Lege Figuren mit Steckbrief, Referenzbildern und Stil-Anker an.
Gewählte Charaktere fließen automatisch in alle Generierungen ein.

✨ Generieren — Beschreibe eine Szene, wähle Figuren (im Charaktere-Tab) und
erzeuge ein konsistentes Bild. Das Ergebnis landet in der Galerie.

🖼️ Galerie — Alle erzeugten Bilder dieses Projekts. Klick → Zoom + Details.
"Als Referenz" übernimmt ein Bild in den Charakter. "🎬" startet ein Video daraus.

🎬 Videos — KI-generierte Clips dieses Projekts. Klick auf Thumbnail → Overlay-Player.
Starte neue Videos aus der Galerie oder per Text/Prompt.

🎵 Audio — Musik und Sprachausgaben. Lyria 3 für Scores, TTS für Dialoge/Voiceover.

🎞️ Filme — Schneide Videos + Musik zu einem fertigen Film zusammen.
Clips per Drag & Drop in die Reihenfolge ziehen.

✂️ Schnitt — Professioneller Videoschnitt: Timeline, Schnitt, Split, Export.
Importiert eigene Videos und die im Projekt generierten Clips.

🎬 Regie — Schreibe ein Drehbuch (Szenen, Charaktere, Dialoge, Musik),
lass den Regieagenten Shots erzeugen und starte den Batch-Render.
```

---

## 4. Galerie-Überarbeitung

### Problem
- `grid-cols-2` = 2 volle Bilder nebeneinander, jedes ~50 % Breite
- Bei 30+ Bildern: endloses Scrollen, alles erschlägt den Nutzer

### Neu: kompaktes Thumbnail-Grid

```tsx
// Ziel-Geometrie:
// Jedes Thumbnail: max(200px, min(250px, calc(100vw / Ncols - gap))
// Ncols: auto-fill mit minmax(200px, 1fr) → Browser wählt je Fensterbreite
// Aspect: quadratisch (object-cover) oder original-Ratio per Toggle

<div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "8px" }}>
```

- Default: `auto-fill`, min 200 px, max 1fr → auf 1920px Breite passen ~8 Bilder pro Reihe
- Toggle oben rechts: **Groß** (minmax(350px, 1fr)) / **Klein** (minmax(150px, 1fr)) / **Liste** (1 Spalte, nur Miniaturvorschau links + Metadaten rechts)
- `object-cover` auf quadratischer Fläche — kein Strecken
- Hover: Overlay mit Buttons (Zoom, Promote, Video, Löschen)
- Klick → Zoom-Overlay (wie bisher, aber volle Viewport-Breite nutzen)
- Sortierung oben: Neueste zuerst / Älteste zuerst / Datum-Gruppe

### Zoom-Overlay (verbessert)
- Bild nimmt 80 vw × 80 vh, bleibt skaliert
- Rechts daneben: Metadaten (Prompt, Modell, Seed, Charaktere, Datum, Dateiname)
- Buttons: Als Referenz übernehmen | Video starten | Herunterladen | Löschen
- Tastatur: ESC schließt, ← → navigiert durch Galerie

---

## 5. Video-Tab-Überarbeitung

### Problem
- Jeder Job = voller `<video>`-Player, alles riesig, keine Übersicht

### Neu: Thumbnail-Grid + Overlay-Player

**Grid** (analog Galerie, aber Seitenverhältnis variabel je nach Clip-Ratio):
```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ ▶ [16:9] │  │ ▶ [9:16] │  │ ⏳ gen…  │
│  3.2s    │  │  5.0s    │  │ Kling v3 │
└──────────┘  └──────────┘  └──────────┘
```

- Fertige Clips: `<video muted loop preload="metadata" onMouseEnter=play onMouseLeave=pause>` → beim Hover läuft Vorschau lautlos
- Laufende Jobs: Spinner + Modell-Name + Progress-Badge
- Klick → **Overlay-Player** (großes Video, Audio an, Controls, Metadaten darunter)
- Im Overlay-Player: Wiederholen (selbe Settings) | Schnitt (→ Schnitt-Tab mit diesem Clip) | Als Startbild (→ letzten Frame extrahieren) | Herunterladen | Löschen

---

## 6. Videoschnitt-Integration (✂️ Schnitt-Tab)

### Ist-Zustand
`videoeditor` ist ein **separates Modul** mit eigenem Nav-Eintrag. Hat eigene
Projektauswahl und Datei-Bibliothek. Nutzt `/api/modules/videoeditor/`.

### Soll-Zustand
Der Schnitt-Tab im Atelier **bettet** den bestehenden VideoEditor ein — kein
eigenes Modul mehr nötig (bleibt aber als Fallback existieren).

#### Option A: Vollständige Einbettung
- `import { EditorView } from "../../videoeditor/frontend/EditorView"`
- Bibliothek zeigt Projekt-Dateien aus **zwei Quellen**:
  1. Eigene Uploads (wie bisher über videoeditor-API)
  2. **Atelier-Clips** dieses Projekts (aus `atelier/videos/*.mp4`)
- BrowseDialog zeigt beide vereint

#### Option B: Deep-Link / Tab-Weiterleitungs-Brücke
- Schnitt-Tab zeigt den VideoEditor als iFrame (einfach, keine Code-Kopplung)
- Nachteil: kein gemeinsamer Zustand, Projekt-Sync schwieriger

**Empfehlung: Option A** — direkter Import, gemeinsamer `projectId`-Kontext.
Sauberer, wartbarer, keine iFrame-Probleme.

#### Was der Schnitt-Tab zusätzlich braucht
- `atelierApi.listVideos(projectId)` → Atelier-Clips anbieten
- In der Datei-Bibliothek des Editors: Gruppe "Atelier-Clips" (neben "Eigene Uploads")
- Export landet nach `atelier/films/<datum>_schnitt_<titel>.mp4` (neues Namensschema)

---

## 7. Neue Datei-Ablage und Benennung

### Problem
Alle generierten Dateien heißen `<32hex>.png` / `<32hex>.mp4` — keine
Rückschlüsse auf Zeitpunkt, Inhalt oder Modell. Schwer zu finden, zu sichten,
zu archivieren.

### Neues Schema

**Grundformat:** `<DATUM>_<SLUG>_<KURZID>.<ext>`

Dabei:
- `DATUM` = `YYYYMMDD` (Generierungsdatum)
- `SLUG` = erster nicht-leerer Begriff aus dem Prompt, max 24 Zeichen,
  nur `[a-z0-9_]` (Sonderzeichen raus, Leerzeichen zu `_`)
- `KURZID` = erste 8 Zeichen der UUID (genug für Eindeutigkeit im Verzeichnis)
- `ext` = `png`, `jpg`, `mp4`, `mp3`, `wav`

**Beispiele:**
```
Vorher:  output/3f2a8b1c4d5e6f7a8b9c0d1e2f3a4b5c.png
Nachher: images/20260708_ritter_am_tor_3f2a8b1c.png

Vorher:  videos/abc123def456789012345678901234ab.mp4
Nachher: videos/20260708_ritter_kling_abc123de.mp4

Vorher:  films/xyz.mp4
Nachher: films/20260708_der_letzte_ritter_xyz012.mp4
```

### Neue Verzeichnisstruktur unter `<workspace>/atelier/`

```
atelier/
  characters/             ← unverändert (chars haben eigene IDs)
    <char-id>/
      character.json
      hero1.png
  images/                 ← NEU statt output/
    <datum>_<slug>_<id>.png   (generierte Bilder)
    <datum>_<slug>_<id>.json  (Sidecar, selber Basename)
  videos/
    <datum>_<slug>_<id>.mp4   (generierte Clips)
    <datum>_<slug>_<id>.json  (Job-Datei = bestehender Job-Store)
  audio/
    <datum>_<slug>_<id>.mp3
    <datum>_<slug>_<id>.json
    profiles/             ← Audio-Profile (unverändert)
  films/
    <datum>_<slug>_<id>.mp4
    <datum>_<slug>_<id>.json
  screenplay/             ← unverändert
  ci.json                 ← unverändert
```

**Migration Altdaten**: beim ersten Zugriff auf ein Projekt wird NICHT
automatisch umbenannt (Breaking Change für bestehende Jobs/Sidecars). Neue
Dateien bekommen das neue Schema. Ein optionaler Backend-Endpoint
`POST /projects/{pid}/atelier/migrate-names` kann auf Wunsch umbenennen.

### `save_image_bytes` / `save_audio_bytes` / `save_video` — Änderung

```python
def _make_name(prompt: str, ext: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:24].strip("_") or "gen"
    date = datetime.now().strftime("%Y%m%d")
    short_id = uuid.uuid4().hex[:8]
    return f"{date}_{slug}_{short_id}.{ext}"

def save_image_bytes(project_id: str, raw: bytes, *, ext: str = "png", prompt: str = "") -> str:
    name = _make_name(prompt, ext)
    (images_dir(project_id) / name).write_bytes(raw)
    return name

# "images_dir" statt "output_dir":
def images_dir(project_id: str) -> Path:
    d = atelier_root(project_id) / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d
```

Backward-Compat: `output_dir` bleibt als Alias auf `images_dir` bis alle
Aufrufer migriert sind. Backend-Route `/gallery` liest aus `images/` (primär)
+ `output/` (Legacy-Fallback).

---

## 8. Ergänzende Features aus der Feedback-Session

### 8a. First+Last-Frame im Video-Dialog (Task `0b8b5fb4`)
- `VideoDialog.tsx`: zweites Bild-Feld "Endbild" (optional)
- `video.py` `_submit_image_to_video`: zweiter `frame_images`-Eintrag `last_frame`
- `media_models.list_video_models()` liefert `supported_frame_images` je Modell
- Endbild-Feld nur anzeigen wenn Modell `last_frame` unterstützt

### 8b. Multi-Referenz-Video (Seedance, Wan 2.7)
- `VideoDialog.tsx`: optionale Charakter-Referenz-Sektion
- Sendung als weitere `frame_images`-Einträge (oder modell-spezifisches `reference_images`-Feld)
- Nur anzeigen wenn Modell `reference_images` unterstützt

### 8c. Emotions-gestütztes TTS (Voxtral)
- In Regie E6: `dialogues[].emotion` → Voice-Mapping auf `voxtral-mini-tts`
  (z.B. `resigniert` → `en_paul_sad`)
- Mapping-Tabelle in `MODELS.md` dokumentieren

---

## 9. Umsetzungs-Etappen

Die Änderungen sind groß aber in saubere, unabhängige Etappen schneidbar:

### Etappe A — Tab-Layout-Umbau (Frontend-only, kein Backend)
- `AtelierPage.tsx`: 3-Spalten-Grid → full-width, Tabs auf 8 erweitern
- Charaktere und FilmPanel aus Seitenspalten in eigene Tabs verschieben
- Onboarding-Banner je Tab (CollapsibleBanner-Komponente, 1 pro Tab)
- **Tests**: kein Backend-Test, nur Build-Check + manuell

### Etappe B — Galerie-Überarbeitung (Frontend-only)
- `Gallery.tsx`: Grid auf `auto-fill minmax(200px, 1fr)` umstellen
- Größen-Toggle (Klein/Mittel/Groß/Liste)
- Zoom-Overlay: Navigation ← → + Metadaten-Panel rechts
- **Tests**: Build-Check + manuell

### Etappe C — Video-Thumbnail-Grid (Frontend-only)
- `VideoPanel.tsx`: Loop-Preview-Thumbnails statt voller Player
- Overlay-Player-Komponente (`VideoOverlay.tsx`)
- **Tests**: Build-Check + manuell

### Etappe D — Videoschnitt-Integration (Frontend + kleiner Backend-Zusatz)
- Schnitt-Tab: `EditorView` einbinden, `projectId` durchreichen
- `videoeditor` Backend-Route: Atelier-Clips als Browse-Quelle
- `BrowseDialog.tsx` im Videoeditor: Gruppe "Atelier-Clips" ergänzen
- **Tests**: bestehende videoeditor-Tests + neuer Integrations-Test

### Etappe E — Datei-Umbenennung (Backend)
- `storage.py`: `images_dir` + `_make_name`
- `save_image_bytes`, `save_audio_bytes`, `save_video` → neues Schema
- `output_dir` als Alias (Legacy-Compat)
- Gallery-Route: liest aus `images/` + `output/` (fallback)
- `migrate-names`-Endpoint (optional, auf Wunsch)
- **Tests**: Storage-Unit-Tests aktualisieren

### Etappe F — First+Last-Frame (Backend + Frontend, Task `0b8b5fb4`)
- Existierender offener Task — hier einplanen, nach A-C umsetzbar

---

## 10. Nicht in dieser Version

- Lippensynchrone Dialog-Animation (TTS-Timing am Video)
- Akt-Ebene im Regie-Tab (E3 aus SPEC-REGIE.md)
- Automatischer Schnitt nach Musiktakt
- Kollaboratives Echtzeit-Editieren

---

## 11. Akzeptanzkriterien

1. Kein 3-Spalten-Grid mehr — alle Funktionen erreichbar über Tabs auf voller Breite.
2. Galerie: `auto-fill`-Grid, Thumbnails ~200–250 px, Größen-Toggle vorhanden.
3. Videos: Loop-Thumbnails, Overlay-Player bei Klick (kein Vollbreite-Player im Grid).
4. Schnitt-Tab nutzt `projectId` und zeigt Atelier-Clips als Quell-Dateien an.
5. Neue Dateien werden nach `images/` abgelegt mit `YYYYMMDD_slug_id.ext`-Schema.
6. Jeder Tab hat eine ein-/ausklappbare Erklärung (was der Tab macht, wie anfangen).
7. `tsc + build` grün, alle bestehenden Backend-Tests unverändert grün.
