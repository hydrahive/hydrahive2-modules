# Atelier — Regie & Drehbuchplaner (Screenplay-Ebene)

> Erweiterung des bestehenden `atelier`-Moduls. Baut auf der vorhandenen
> Charakter-/CI-Bibliothek, den Regie-Presets, dem Generator, den Video-Jobs
> und dem Film-Zusammenschnitt auf. **Status: Design / noch nicht implementiert.**

## Problem

Das Atelier erzeugt heute einzelne Bilder/Clips ohne narrative Struktur. Es
fehlt die Ebene *dazwischen*: ein ganzes Filmprojekt als geordnete Szenenfolge
planen, Figuren + Regie-Anweisungen + Dialoge + Musik je Szene zuweisen, Szenen
umordnen — und das komplette Drehbuch dann an einen **Regieagenten** geben, der
es in generierbare Shots zerlegt, dem User vorlegt und nach Freigabe abfährt.

## Zielbild (Tills Ablauf, verbatim übernommen)

1. **Filmprojekt anlegen** → wählt Film-Modell (Video) + Audio-/Musik-Modell.
2. **Charaktere zuweisen** (existiert bereits: Charakter-Bibliothek pro Projekt).
3. **Charakter-Bilder / Aussehen generieren** (existiert bereits: Generator + Referenzen).
4. **Regie öffnen** → Gesamt-Beschreibung des Films (Genre, Ton, Look, Story-Idee).
5. **Szene hinzufügen** → Szene beschreiben, mitspielende Charaktere zuweisen,
   Dialoge eintragen, optionale Musik-Untermalung, Regie-Presets wählen → Szene speichern.
6. Schritt 5 wiederholen für Szene 2, 3, … · Szenen **umordnen** (Drag & Drop).
7. **Regiescript absenden** an den Regieagenten → er **zerlegt** alles
   (Szenen → Shots mit Kamera/Prompt/Dauer/Charakter-Bindung), **legt es vor**.
8. User prüft, korrigiert ggf., sagt **OK** → Batch-Generierung läuft
   (Bild → Video-Clip je Shot → Szenen-Verkettung → Film-Zusammenschnitt + Audio).

## Datenmodell — 3 Ebenen (Akt → Szene → Shot)

Dateibasiert im Projekt-Workspace, konsistent zum bestehenden Atelier-Pattern.
Neuer Unterordner:

```
<projekt-workspace>/atelier/
  screenplay/
    screenplay.json          # Kopf: Titel, Beschreibung, Modelle, Akt-Reihenfolge
    acts/<act-id>.json       # Akt: Titel, Notiz, Szenen-Reihenfolge (scene-ids)
    scenes/<scene-id>.json   # Szene: Beschreibung, Charaktere, Dialoge, Musik, Presets, Shot-Reihenfolge
    shots/<shot-id>.json     # Shot: Prompt, Kamera-Presets, Startbild, Dauer, Status, video_rel
```

### `screenplay.json` (ein Drehbuch je Projekt)
```jsonc
{
  "title": "Der letzte Ritter",
  "logline": "Ein Ritter kehrt in seine zerstörte Heimat zurück …",
  "description": "Düsterer Fantasy-Kurzfilm, gedämpfte Farben, epische Weite.",
  "film_model": "google/veo-3.1",            // Video-Modell fürs ganze Projekt
  "audio_model": "google/lyria-3-pro-preview", // Musik-Modell
  "voice_model": "…",                          // optional: TTS für Dialoge
  "aspect_ratio": "16:9",
  "default_duration": 5,
  "act_order": ["<act-id-1>", "<act-id-2>"],
  "created_at": "…", "updated_at": "…"
}
```

### `acts/<act-id>.json`  (Ebene B — optional; Default: 1 Akt)
```jsonc
{ "id": "…", "title": "Akt 1 — Ankunft", "note": "", "scene_order": ["<scene-id>", …] }
```
> Wer die Hierarchie nicht braucht, arbeitet in genau einem Default-Akt —
> die Akt-Ebene bleibt unsichtbar/eingeklappt. So bekommt Option A (flache
> Szenenliste) und Option B (volle Hierarchie) dasselbe Modell.

### `scenes/<scene-id>.json`  (Ebene — das Herzstück, hier arbeitet der User)
```jsonc
{
  "id": "…",
  "title": "Szene 1 — Ruinentor",
  "description": "Der Ritter tritt bei Sonnenuntergang durch das zerbrochene Tor.",
  "character_ids": ["<char-id>", …],          // wer spielt mit (aus der Bibliothek)
  "dialogues": [
    { "character_id": "<char-id>", "line": "Ich bin zu spät gekommen.", "emotion": "resigniert" }
  ],
  "music": { "enabled": true, "prompt": "melancholisches Cello, langsam", "music_rel": null },
  "camera": { "shot": "wide", "lens": "35mm", "light": "golden_hour", "mood": "somber" }, // Regie-Presets (Default für Szene)
  "location": "Zerstörte Burgruine",
  "time_of_day": "sunset",
  "shot_order": ["<shot-id>", …],             // vom Regieagenten befüllt
  "created_at": "…", "updated_at": "…"
}
```

### `shots/<shot-id>.json`  (Ebene A — was tatsächlich generiert wird = 1 Clip)
```jsonc
{
  "id": "…", "scene_id": "…",
  "order": 0,
  "prompt": "Wide shot, knight silhouette in broken gate, golden sunset …", // vom Agenten
  "camera": { "shot": "wide", "lens": "35mm", "light": "golden_hour" },     // Shot-spezifisch, überschreibt Szene
  "character_ids": ["<char-id>"],             // im Shot sichtbar → Referenzbilder in den Prompt
  "start_image_rel": null,                    // Startbild: generiert oder Continue-Frame des Vorgänger-Shots
  "duration": 5,
  "dialogue_ref": 0,                          // Index in scene.dialogues (für TTS/Untertitel), optional
  "status": "planned",                        // planned | image_ready | video_processing | done | failed
  "image_rel": null, "video_rel": null, "error": null
}
```

## Der Regieagent (Kern-Feature C)

Ein **projekt-interner Spezialist** ("Regieagent") bekommt das fertige Drehbuch
als strukturiertes JSON und zerlegt es. Klar getrennt in zwei Phasen mit
User-Gate dazwischen — Till sagt explizit "legt es mir vor und ich sage ok".

### Phase 1 — Zerlegen & Vorlegen (kein Generieren)
Input: `screenplay.json` + alle Szenen + Charakter-Steckbriefe + CI.
Aufgabe des Agenten:
- Jede Szene in 1–N **Shots** aufteilen (Establishing/Wide → Medium → Close etc.).
- Pro Shot einen **präzisen englischen Video-Prompt** bauen aus:
  Szenenbeschreibung + Charakter-Style-Anchors + Kamera-Presets + Location/Zeit.
- Kamera-Presets je Shot sinnvoll wählen (Schnittrhythmus, Achsensprung vermeiden).
- Charakter-Bindung setzen (welche Referenzbilder in welchen Shot).
- Startbild-Strategie: Shot 1 der Szene = neu generiertes Keyframe;
  Folge-Shots = Continue-Frame des Vorgängers (nutzt vorhandenes `continueFrame`).
- Dauer je Shot vorschlagen.
**Output: Shot-Liste als Vorschau** (schreibt `shots/*.json` mit status=`planned`,
befüllt `scene.shot_order`). **Nichts wird generiert.** → UI zeigt Storyboard-Vorschau.

### User-Gate
User sieht die zerlegten Shots je Szene (Prompt, Kamera, Charaktere, Dauer),
kann editieren / löschen / neu anordnen / Shot hinzufügen. Knopf **"Freigeben & generieren"**.

### Phase 2 — Batch-Generierung (nach OK)
Fährt die Shots der Reihe nach ab, nutzt **ausschließlich vorhandene Bausteine**:
1. Keyframe-Bild je Shot → bestehender `generate`-Endpoint (Charaktere+Presets).
2. Bild → Video-Clip → bestehender `videos`-Endpoint (Film-Modell aus screenplay).
3. Continue-Frame-Verkettung innerhalb der Szene → bestehender `continue`-Endpoint.
4. Musik je Szene → bestehender Audio/Music-Pfad.
5. Alle Clips (+ Musik) → bestehender `films`-Zusammenschnitt.
Status je Shot wird live hochgezählt (`planned → image_ready → video_processing → done`).

## Neue Backend-Routen (unter dem bestehenden atelier-Router)

Alle project-scoped, `require_auth` + `_guard` wie gehabt:

```
GET    /projects/{pid}/screenplay                 → screenplay.json (oder leeres Default)
PUT    /projects/{pid}/screenplay                 → Kopf speichern (Titel, Modelle, …)

GET    /projects/{pid}/screenplay/acts            → Akte (geordnet)
POST   /projects/{pid}/screenplay/acts            → Akt anlegen
PUT    /projects/{pid}/screenplay/acts/{id}       → Akt ändern (Titel, scene_order)
DELETE /projects/{pid}/screenplay/acts/{id}

GET    /projects/{pid}/screenplay/scenes          → Szenen (geordnet)
POST   /projects/{pid}/screenplay/scenes          → Szene anlegen
PUT    /projects/{pid}/screenplay/scenes/{id}     → Szene ändern (Beschreibung, Chars, Dialoge, Musik, Presets)
DELETE /projects/{pid}/screenplay/scenes/{id}
POST   /projects/{pid}/screenplay/scenes/reorder  → Reihenfolge (Drag&Drop) speichern

GET    /projects/{pid}/screenplay/scenes/{id}/shots
PUT    /projects/{pid}/screenplay/scenes/{id}/shots/{sid}   → Shot editieren (nach Vorlage)
POST   /projects/{pid}/screenplay/scenes/{id}/shots/reorder

POST   /projects/{pid}/screenplay/decompose       → Phase 1: an Regieagent, füllt shots (planned)
GET    /projects/{pid}/screenplay/decompose/{job} → Zerlege-Job-Status (async)
POST   /projects/{pid}/screenplay/render          → Phase 2: Batch-Generierung starten (nach OK)
GET    /projects/{pid}/screenplay/render/{job}    → Render-Job-Fortschritt (pro Shot)
```

## Frontend (neuer Tab "Regie" im Atelier)

- **Tab-Leiste** ergänzt um **🎬 Regie** neben Galerie/Video/Film.
- **Drehbuch-Kopf**: Titel, Logline, Beschreibung, Film-/Audio-Modell-Auswahl,
  Aspect-Ratio, Default-Dauer.
- **Szenen-Liste** (Karten, Drag&Drop-Reorder). Je Karte:
  Titel, Beschreibung, Charakter-Chips (aus Bibliothek), Dialog-Zeilen-Editor,
  Musik-Toggle+Prompt, Regie-Preset-Dropdowns (`CameraControls` wiederverwenden).
- **Akt-Gruppierung** optional einklappbar (Ebene B; Default 1 Akt = unsichtbar).
- **"An Regieagent senden"** → Zerlege-Job → **Storyboard-Vorschau** (Shots je Szene).
- **Freigabe-Gate**: Shots editierbar, dann **"Freigeben & generieren"** → Fortschritt.

## Wiederverwendung (was NICHT neu gebaut wird)

| Bereits vorhanden | Nutzung in Regie |
|---|---|
| Charakter-Bibliothek + Referenzen | Szenen-/Shot-Charakter-Zuweisung |
| CI (Palette/Style-Anchor) | Konsistenter Look über alle Shots |
| Regie-Presets (`presets`, `CameraControls`) | Kamera je Szene/Shot |
| `generate` (Bild) | Keyframe je Shot |
| `videos` (Bild→Video) + `continue` | Clip je Shot + Szenen-Verkettung |
| `films` (Zusammenschnitt) | Finaler Film + Musik |
| Audio/Music-Pfad | Szenen-Untermalung |
| Job-Store (`_jobstore.py`) | Zerlege- + Render-Jobs (async, Status-Polling) |
| Projekt-Guard / Storage-Pattern | Screenplay-Persistenz, kein Traversal |

## Nicht in v1 (bewusst ausgeklammert)

- Lippensynchrone Dialog-Animation (nur TTS-Voiceover + optionale Untertitel).
- Automatischer Schnitt nach Beat/Musik-Takt.
- Kollaboratives Echtzeit-Editieren mehrerer User am selben Drehbuch.
- Export als Fountain/Final-Draft-Format (später denkbar).

## Akzeptanzkriterien

1. User legt ein Drehbuch mit Titel, Beschreibung, Film-/Audio-Modell an — persistiert.
2. User fügt ≥2 Szenen hinzu, beschreibt sie, weist Charaktere + Dialoge + Musik zu,
   ordnet sie per Drag&Drop um — alles bleibt nach Reload erhalten.
3. "An Regieagent senden" erzeugt je Szene eine Shot-Liste (Prompt+Kamera+Charaktere),
   ohne etwas zu generieren; die Vorschau ist editierbar.
4. Nach "Freigeben & generieren" entstehen Keyframes → Clips → verketteter Film
   mit Musik, ausschließlich über die vorhandenen generate/videos/films-Pfade.
5. Kein Zugriff über Projektgrenzen (Guard), keine Path-Traversal-Lücke.
6. Backend-Tests grün, ruff clean, spec-guard grün.

## Umsetzungs-Etappen (Vorschlag)

- **E1 — Datenmodell + CRUD:** storage/screenplay + Routen (Kopf, Szenen, Reorder),
  Tests. Kein Agent, kein Generieren. → sofort nutzbar als reiner Planer.
- **E2 — Regie-Tab Frontend:** Drehbuch-Kopf, Szenen-Karten, Dialoge, Presets, Reorder.
- **E3 — Akt-Ebene (B):** optionale Gruppierung ein-/ausklappbar.
- **E4 — Regieagent Phase 1:** Zerlegen → Shot-Vorschau (Storyboard), Gate-UI.
- **E5 — Batch-Render Phase 2:** Keyframe→Clip→Continue→Film-Merge, Fortschritt.
- **E6 — Dialog-Voiceover/Untertitel + Feinschliff.**
```
