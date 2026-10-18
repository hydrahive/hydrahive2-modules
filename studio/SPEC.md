# Studio – ein Ort für Bild, Video, Ton und Schnitt

> Neues Modul `studio`. Es löst **Atelier**, **Video-Editor** und **Tonstudio** sowie den Videoschnitt im Kern-Cockpit
> („Medien“) ab. Am Ende verschwinden die alten Module (Till, 15.10.2026).
> **Status: Spec, Etappe 0 (Attrappe) in Arbeit.**
> Recherche (nur Prinzipien, nichts kopiert): `_work/scratch/studio-research/ERGEBNIS.md` (DaVinci Resolve, Kdenlive,
> OpenCut, Descript, LTX Studio). Ideen für Untertitel und Übersetzen: OpenCreator (Apache-2.0).

## Problem

Heute ist Medienarbeit über vier Stellen verstreut:
- **Atelier:** Figuren, Bilder, Videos, Drehbuch, Regie, Film.
- **Video-Editor:** Zeitleiste, Ton, Export.
- **Tonstudio:** Musik.
- **Medien-Cockpit im Kern:** Videoschnitt, eingebunden über `mediaWorkflows`/`mediaSources`.

Wer einen Film macht, springt hin und her, und dieselben Dateien tauchen an mehreren Stellen unterschiedlich auf. Dazu
gibt es zu viele Module für ein Thema.

## Ziel

Ein Modul **Studio**. Es hat eine Oberfläche, wie man sie aus Schnittprogrammen kennt, und alles an einem Ort: planen,
erzeugen, schneiden, vertonen, untertiteln, ausgeben. Man arbeitet ohne Unterbrechung: Was erzeugt wird, liegt sofort in
der Bibliothek und lässt sich auf die Zeitleiste ziehen.

## Grundsätze (aus der Recherche)

1. **Bekanntes Gerüst:** Bibliothek links, Vorschau in der Mitte, Eigenschaften rechts, Zeitleiste unten. Die Größen
   lassen sich ziehen und werden je Nutzer gespeichert.
2. **Arbeitsbereiche nach Schritt** (Reiter oben): Es ist immer nur das sichtbar, was der Schritt braucht. Die Daten
   sind überall dieselben.
3. **Schnell, nicht abgespeckt:** Es gibt ein Bedienkonzept mit klugen Voreinstellungen, keinen getrennten
   Anfänger- und Profi-Modus. Profi-Funktionen sind vorhanden, stehen aber nicht im Weg.
4. **Nicht zerstörend:** Originale bleiben unangetastet, Schnitte sind Projektdaten. Proxies sorgen für eine flüssige
   Vorschau, gerendert wird im Hintergrund mit sichtbarem Stand.
5. **KI ist Teil des Ablaufs, kein eigenes Programm:** Ein Platzhalter-Clip auf der Zeitleiste wird mit „Erzeugen“
   gefüllt. Varianten liegen nebeneinander, eine wird übernommen.
6. **Tastatur zuerst:** Standard-Kürzel, wie Schnittleute sie erwarten, dazu `Strg+K` für alle Befehle. Ein Hilfe-Dialog
   zeigt alle Kürzel.

## Arbeitsbereiche

| Reiter | Inhalt | Kommt aus |
|---|---|---|
| **Planen** | Drehbuch: Akte, Szenen, Shots, Dialoge, Regie-Vorgaben. Bausteine: Figuren, Orte, Objekte. Look (CI). | Atelier (screenplay, characters, director) |
| **Erzeugen** | Bild, Video, Sprache, Musik. Varianten vergleichen, eine übernehmen. Modellwahl, Kosten-Hinweis. | Atelier (generate, video, audio), Tonstudio |
| **Schneiden** | Zeitleiste mit Video-, Bild-, Text- und Tonspuren, Trimmen, Teilen, Einrasten, Marker. | Video-Editor, Kern-Videoschnitt |
| **Ton** | Spuren-Mixer: Lautstärke, Stumm/Solo, Pegel, Wellenform, Musik und Sprache. | Video-Editor (Audio), Atelier (Audio) |
| **Untertitel** | Untertitelspur als eigene Daten, Transkribieren, Übersetzen, zweisprachig, Stil. Später Vertonung. | neu (Ideen aus OpenCreator) |
| **Ausgabe** | Render-Vorlagen (16:9, 9:16, 1:1), Warteschlange, fertige Dateien, SRT. | Video-Editor (Export), Atelier (Film) |

Bibliothek, Vorschau, Eigenschaften und Zeitleiste bleiben in allen Reitern an ihrem Platz. Je Reiter ändert sich, was in
den Seitenleisten steht und welche Werkzeuge die Zeitleiste zeigt. In „Planen“ ist die Zeitleiste zum Beispiel eine
Szenen-Leiste (Storyboard), in „Ton“ stehen die Tonspuren groß im Vordergrund.

## Oberfläche (Etappe 0 = Attrappe dieses Aufbaus)

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ Studio · [Projekt ▾]   Planen  Erzeugen  Schneiden  Ton  Untertitel  Ausgabe   ⌘K  ⓘ  │
├──────────────┬─────────────────────────────────────────────┬──────────────────────────┤
│ BIBLIOTHEK   │                VORSCHAU                     │ EIGENSCHAFTEN            │
│ [Alle|Video| │   ┌─────────────────────────────────────┐   │ (zum gewählten Clip /    │
│  Bild|Ton|   │   │                                     │   │  Shot / Spur)            │
│  Figuren]    │   │                                     │   │                          │
│ 🔍 Suchen    │   └─────────────────────────────────────┘   │ Erzeugen-Panel im Reiter │
│ ▸ KI-erzeugt │   ⏮ ◀◀ ▶ ▶▶ ⏭   00:00:12:04 / 00:01:30   │ „Erzeugen“               │
│ ▸ Hochgeladen│   [16:9 ▾] [Proxy ●]                        │                          │
│ ▸ Musik      │                                             │                          │
├──────────────┴─────────────────────────────────────────────┴──────────────────────────┤
│ ÜBERSICHT  ▕▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▏ (ganzer Film)   │
│ V2 Text    │      [Titel]                                                             │
│ V1 Video   │ [Shot 1 ][Shot 2   ][ ⟡ Platzhalter: erzeugen ][Shot 4]                   │
│ A1 Sprache │ [~~~~~ Dialog ~~~~~]                                                     │
│ A2 Musik   │ [≈≈≈≈≈≈≈≈≈≈≈≈≈≈ Musik ≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈≈]                                 │
│ S1 Untert. │ [Hallo…][Wo bist…]                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

- **Übersichtsleiste** über der Zeitleiste zeigt den ganzen Film klein. Die Zeitleiste darunter zeigt den gezoomten
  Ausschnitt, Ziehen in der Übersicht verschiebt den Ausschnitt. Das ist die Idee „doppelte Zeitleiste“.
- **Platzhalter-Clip:** ein Shot ohne Medium (aus dem Drehbuch). Ein Klick öffnet im rechten Panel „Erzeugen“ mit
  Prompt, Figuren und Kamera aus dem Shot. Das Ergebnis ersetzt den Platzhalter, alte Varianten bleiben in der
  Bibliothek.
- **Bibliothek:** eine Liste für alles, mit Filtern und automatischen Ordnern (KI-erzeugt, Hochgeladen, Musik, Altbestand
  Atelier).
- **Statuszeile** unten oder in der Kopfzeile zeigt laufende Aufträge (Erzeugen, Proxy, Rendern) mit Fortschritt. Ein
  Klick öffnet die Warteschlange.

## Tastenkürzel (Standard, anpassbar)

| Taste | Aktion |
|---|---|
| Leertaste / K | Abspielen / Pause |
| J / L | Zurück / Vor (mehrfach drücken = schneller) |
| ← / → | Ein Bild zurück / vor |
| Shift + ← / → | 5 Sekunden zurück / vor |
| Pos1 / Ende | Anfang / Ende |
| S | Teilen am Abspielkopf |
| Q / W | Teilen und links / rechts löschen |
| Entf | Auswahl löschen |
| Strg + C / V / D | Kopieren / Einfügen / Verdoppeln |
| N | Einrasten an/aus |
| M | Marker setzen |
| Strg + Z / Strg + Shift + Z | Rückgängig / Wiederholen |
| Strg + K | Befehlssuche |
| ? | Alle Kürzel anzeigen |

Kürzel wirken nicht, solange der Fokus in einem Eingabefeld liegt.

## Daten

**Ein Ordner je Projekt:** `<projekt-workspace>/studio/`.

```
studio/
  project.json          # Einstellungen: Format, Bildrate, Standard-Modelle, Look (CI)
  library/              # Medien: images/ videos/ audio/ music/ uploads/  (+ .json je Datei: Herkunft, Prompt, Modell)
  elements/             # Bausteine: characters/ places/ objects/  (heute atelier/characters)
  screenplay/           # Akte, Szenen, Shots (heute atelier/screenplay)
  timelines/<id>.json   # Schnittfassungen (EDL): Spuren, Clips, Marker, Untertitel-Referenzen
  subtitles/<id>.json   # Untertitel je Sprache (Segmente mit Zeit), Stil
  cache/                # proxies/ sprites/ peaks/ – jederzeit neu erzeugbar
  renders/              # fertige Ausgaben
  jobs/                 # Auftragszustände (Neustart-fest)
```

- Pfade laufen über die vorhandenen Hilfen (`ensure_workspace`, `safe_under`), keine festen Pfade.
- Proxies und Wellenformen liegen nur im Cache und sind wegwerfbar.

## Übernahme der alten Daten (letzte Etappe, vorher Spec-Nachtrag)

- In Admin → Module, oder beim ersten Öffnen eines Projekts im Studio, gibt es „Daten aus Atelier, Video-Editor und
  Tonstudio übernehmen“.
- Ablauf: kopieren, prüfen, dann umstellen. Die alten Ordner bleiben zunächst stehen, ihr Inhalt landet erst später im
  Archiv (das Archiv-System kennt das).
- Prod-Stand 15.10.: Atelier 18 Projekte / 157 MB, Video-Editor 2 / 10 MB, Tonstudio 1 / 5 MB.
- Agenten-Werkzeuge `atelier_*` bekommen Nachfolger `studio_*`. Der Skill `atelier-workflow` wird zu `studio-workflow`.
- Erst wenn die Übernahme auf Prod gelaufen ist, werden die alten Module entfernt, ebenso der Medien-Reiter im
  Kern-Cockpit samt `mediaWorkflows`/`mediaSources`.

### Endzustand der Hauptleiste (Till, 15.10.)

Am Ende gibt es für Medien **nur noch „Studio“**, damit die Leiste oben leerer und übersichtlicher wird:
- **Weg:** die Module Atelier, Video-Editor und Tonstudio (Eintrag in der Leiste, Modul, `hub.json`).
- **Weg aus dem Kern** (eigener Kern-PR in Etappe 8):
  - der feste Reiter **„Media“** (`CORE_NAV` in `CockpitTopbar.tsx`, `QUICK_LINK_PATHS`, `nav-config.ts`, Route `/media`,
    `MediaCockpitPage` mit `features/cockpit/media/`)
  - die Verweise darauf (`BuddyPage` primaryLinks, `extensions/types.ts`, Hilfe-Thema `atelier`)
  - Alte Links auf `/media`, `/atelier`, `/videoeditor` und `/tonstudio` leiten auf `/studio` weiter.
- **Bleibt:** „Studio“ als Modul-Reiter (`cockpit: true`). Der Kern hängt nicht vom Studio ab: Fehlt es, gibt es
  einfach keinen Medien-Reiter.
- Installationen, die wir nicht kennen: Übernahme und Abschalten laufen über die Admin-Konsole bzw. automatisch beim
  Update, ohne Terminal. Kein Server verliert Daten. Die Inhalte der alten Ordner landen im Archiv.

## Etappen (je Etappe: Spec-Nachtrag → Tests → Code → Prüfung → PR → Tills OK)

| # | Inhalt | Nutzbar danach |
|---|---|---|
| **0** | **Klickbare Attrappe** auf hydratest: Layout, Reiter, Panels ziehbar, Tastenkürzel-Hilfe, Beispieldaten. Kein Backend. ✅ | Till beurteilt Aufbau und Gefühl im Browser |
| 1 | Gerüst echt: Projektwahl, Bibliothek liest alle vorhandenen Medien (Atelier, Video-Editor, Tonstudio, Uploads – nur lesend), Vorschau spielt ab, Panelgrößen gespeichert | Medien aller Module an einem Ort ansehen |
| 2 | **Planen:** Drehbuch (Akte, Szenen, Shots), Bausteine (Figuren, Orte, Objekte), Look, Storyboard-Leiste, Regie-Agent | Film im Studio planen |
| 3 | **Erzeugen:** Bild und Video je Shot (3a, 3b), mehrere auf einmal als Auftrag (3c), Varianten, Ergebnis direkt in der Bibliothek. Sprache/Musik → Etappe 5 | Vom Drehbuch zu fertigen Shots |
| 4 | Schneiden: Zeitleiste mit Spuren, ziehen, trimmen, teilen, Einrasten, Rückgängig, Übersichtsleiste, Proxies | Schnitt im Studio |
| 5 | Ton: Tonspuren, Mixer, Wellenform, Pegel, Musik und Sprache auf der Zeitleiste | Vertonen im Studio |
| 6 | Untertitel: aus Sprechtexten oder herausgehört, Spur, Übersetzen, SRT/WebVTT als Dateien (nie eingebrannt) | Untertitel und Übersetzung |
| 7 | Ausgabe: Render-Vorlagen, Warteschlange im Hintergrund, Ergebnisse in der Bibliothek | fertige Videos aus dem Studio |
| 8 | Übernahme alter Daten, Nachfolger für die Agenten-Werkzeuge, alte Module und Kern-Reiter „Media“ entfernen | nur noch „Studio“ |
| später | Text-Schnitt über Transkript (Descript-Prinzip), Vertonung in Zielsprache, Farbe, Effekte, Übergänge | |

## Bauplan Etappe 1 – Gerüst mit echter Bibliothek (15.10.)

**Nur lesen.** Etappe 1 schreibt nichts in die Ordner der alten Module und legt auch noch keinen `studio/`-Ordner an.

**Backend: `GET /api/modules/studio/projects/{id}/library`** liefert eine Liste aller Medien des Projekts.
- **Atelier** (`atelier/`):
  - `images/*` und `output/*` (Bild, Begleitdatei `.json` mit `prompt`)
  - `videos/*.json` (nur `status == "completed"`, Video unter `video_rel`, `prompt`, `model`, `duration`)
  - `films/*` (Video)
  - `audio/*.mp3|wav|…` (Musik/Sprache, `.json` mit `prompt`, `model`)
  - `characters/<id>/character.json` als Baustein `element` (Name, erstes Bild als Vorschau)
- **Video-Editor** (`videoeditor/originals/*`): Video, Herkunft „hochgeladen“.
- **Tonstudio** (`tonstudio/clips/*.{mp3,…}` + `.json`): Musik, `name`, `prompt`, `model`.
- Eintrag: `id` (stabil: Hash aus Pfad), `kind` (video, image, audio, music, element), `name`, `origin` (ai, upload),
  `source` (atelier, videoeditor, tonstudio), `rel` (Pfad relativ zum Projekt), `abs` (für `/api/files`), `size`,
  `created_at`, optional `duration`, `prompt`, `model`, `thumb_abs`.
- Sicherheit:
  - Nur Mitglieder des Projekts (`list_for_user`), sonst 404 `studio_project_not_found`. Projekt-ID wird geprüft.
  - Symlinks und alles außerhalb des Projektordners werden übersprungen.
  - Kaputte `.json` ignorieren, die Datei erscheint trotzdem (Name aus dem Dateinamen).
- Grenze: höchstens 5.000 Einträge je Abruf (Konstante im Modul), neueste zuerst. Mehr hat auf Prod
  heute kein Projekt.
- **Ausliefern** der Dateien über den Kern (`/api/files`, mit Range, Rechteprüfung). Das Modul bekommt keinen eigenen
  Datei-Endpunkt.

**Frontend:**
- Die Projektwahl oben listet die Projekte des Nutzers. Zuletzt gewählt wird im Browser gemerkt.
- Die Bibliothek zeigt die echten Einträge mit Filtern, Suche und Ordnern. Die Herkunftsordner heißen jetzt „KI-erzeugt“,
  „Hochgeladen“ und je Quelle „Aus dem Atelier“, „Aus dem Video-Editor“, „Aus dem Tonstudio“.
- Vorschaubilder: Bilder direkt. Videos per `<video preload="metadata">`, das erste Bild genügt. Für Musik ein Symbol.
- Ein Klick wählt den Eintrag, die Vorschau zeigt bzw. spielt das echte Medium (`<video>`, `<img>`, `<audio>`), mit
  Transportleiste, Zeitcode und Tastenkürzeln am echten Medium.
- Die Eigenschaften zeigen Name, Art, Herkunft, Größe, Datum, Prompt und Modell.
- Zeitleiste und Storyboard bleiben Beispieldaten (Hinweis bleibt) bis Etappe 2/4. Leeres Projekt: freundlicher Hinweis
  statt leerer Fläche.

**Nicht in Etappe 1:** Hochladen, Löschen, Umbenennen, Ordner anlegen.

## Bauplan Etappe 2 – Planen (15.10.)

**Till, 15.10.:** eigener `studio/`-Ordner von Anfang an, damit Ordnung ins Projekt kommt. Atelier-Daten werden per Knopf
**kopiert**, das Atelier bleibt unangetastet. Danach gelten die Daten im Studio. Was später noch im Atelier geändert wird,
sieht das Studio nicht mehr (Hinweis im Dialog).

**Daten** (unter `<projekt>/studio/`, nur das Studio schreibt hier):
```
studio/
  screenplay.json            # Kopf: title, logline, description, aspect_ratio, default_duration, models{video,image,voice,music}, look{style,palette[]}, scene_order[]
  scenes/<id>.json           # title, description, location, time_of_day, element_ids[], dialogues[{element_id,line,emotion}], camera{shot,lens,light,weather,time,mood}, shots[]
  elements/<id>/element.json # kind (character|place|object), name, description, style_anchor, palette[], references[] (rel. zum Projekt)
  imported.json              # wann/von wo übernommen (Atelier), was übernommen wurde
```
- Die Shots liegen **in der Szene** (`shots[]`: id, order, shot, prompt, element_ids, duration, status, image_rel,
  video_rel). Es gibt keine eigene Datei je Szene mehr, damit Szene und Shots nie auseinanderlaufen.
- IDs: 32 Hex-Zeichen (wie Atelier), geprüft. Längen und gültige Werte wie im Atelier (Titel 200, Beschreibung 4000,
  Dialog 2000, ≤ 100 Dialoge, ≤ 32 Bausteine, Dauer 1–60 s, Status `planned|image_ready|video_processing|done|failed`,
  Kamera-Schlüssel aus einer festen Liste).
- Schreiben ist atomar (`.tmp` + `os.replace`), damit nie eine halbe Datei liegt.
- Referenzbilder sind Pfade aus der Bibliothek (relativ zum Projekt, nur Bilder im Projekt, keine Symlinks).

**Übernahme aus dem Atelier** (`POST …/import/atelier`, idempotent):
- Kopiert screenplay.json, scenes/*.json (dabei `character_ids` → `element_ids`), shots/<scene>.json (→ `shots[]` der
  Szene), characters/<id>/character.json (→ `elements/<id>/element.json`, kind `character`), ci.json (→ `look`).
- Gleiche IDs, Referenzbilder bleiben, wo sie sind (`atelier/characters/<id>/…`, nur lesen).
- Gibt es im Studio schon Planungsdaten, wird nichts überschrieben (409 `studio_plan_exists`).
- Zeigt vorher, was übernommen würde (`GET …/import/atelier` → Anzahl Szenen, Shots, Figuren, Look ja/nein).

**Regie-Agent** (`POST …/scenes/{id}/decompose`, `POST …/decompose`): Szene → Shots per LLM, Prompt angelehnt an den
Atelier-Regieagenten (gleiche Regeln: 2–5 Shots, nur erlaubte Shot-Arten, nur Bausteine der Szene). Ersetzt die Shots
der Szene. Bei Fehler bleiben die alten Shots und eine klare Meldung erscheint. Modell: `models.text` aus dem Kopf, sonst
der Standard. Läuft im Hintergrund nur so lange wie die Anfrage dauert (kein eigener Auftrag in Etappe 2).

**Frontend „Planen“:**
- Links: **Drehbuch-Gliederung** (Kopf, Szenen in Reihenfolge, Hoch/Runter). Darunter die **Bausteine** (Figuren,
  Orte, Objekte). Die Bibliothek bleibt über einen Reiter erreichbar.
- Mitte: Vorschau des gewählten Shots bzw. des Referenzbilds der Figur.
- Rechts: Formular des Gewählten (Kopf, Szene, Shot, Baustein), Speichern mit Rückmeldung, Löschen über Dialog (kein
  `confirm()`).
- Unten: Storyboard aus den echten Shots der gewählten Szene, Knopf „In Shots zerlegen“.
- Leeres Studio, Atelier hat Daten: Hinweis „Aus dem Atelier übernehmen“ mit Vorschau der Mengen.

**Aufteilung:**
- **2a:** Daten, Übernahme, Kopf/Szenen/Bausteine (Backend + Frontend).
- **2b:** Shots bearbeiten, Storyboard echt, Regie-Agent.

### Bauplan 2b – Shots und Regie-Agent (17.10.)

**Stand nach 2a:** Shots liegen in `scenes/<id>.json` → `shots[]` und werden im Storyboard angezeigt. Bearbeiten lassen
sie sich noch nicht. Der Regie-Agent des Ateliers (`atelier/backend/director.py`) ist das Vorbild.

**Backend** (neue Datei `backend/shots.py`, Routen in `backend/shot_routes.py`, alles mit Mitgliedschaftsprüfung):
- `POST …/plan/scenes/{sid}/shots`: neuer Shot am Ende der Szene. Standarddauer aus dem Kopf (`default_duration`),
  Status `planned`.
- `PUT …/plan/scenes/{sid}/shots/{id}`: Kamera (`shot`), Beschreibung (`prompt`), Bausteine, Dauer. Status und
  Mediendateien (`image_rel`, `video_rel`) ändert nur das Erzeugen (Etappe 3), nicht dieses Formular.
- `DELETE …/plan/scenes/{sid}/shots/{id}`.
- `PUT …/plan/scenes/{sid}/shots/order` mit `{shot_ids: [...]}` setzt die Reihenfolge. Unbekannte IDs fallen weg,
  fehlende kommen hinten an.
- Bausteine eines Shots: nur die der Szene (`element_ids` der Szene). Prüfung wie in 2a; Längen bleiben gleich.
- `POST …/plan/scenes/{sid}/decompose` (**Regie-Agent**):
  - Szene → 2–5 Shots per LLM.
  - Prompt nach dem Vorbild des Atelier-Regieagenten: eigene Kopie im Studio, kein Import über die Modulgrenze.
    Erlaubt sind nur die Shot-Arten aus den Vorgaben und nur die Bausteine der Szene. Der Look aus dem Kopf und das
    Aussehen der Bausteine kommen in den Kontext.
  - Modell: `models.text` aus dem Kopf, sonst der Standard des Servers (`llm_client.complete(model=None)`).
  - **Ersetzt** die Shots der Szene nur bei Erfolg. Bei LLM-Fehler oder unbrauchbarer Antwort bleiben die alten Shots,
    und die Antwort ist 502 `studio_decompose_failed` mit klarer Meldung.
  - Shots mit Bild oder Video gehen beim Ersetzen nicht stillschweigend verloren: Hat die Szene schon Shots mit
    Medien, ist die Antwort 409 `studio_decompose_has_media`. Das Frontend fragt dann in einem eigenen Dialog nach und
    schickt `{"replace": true}`. Die Mediendateien selbst bleiben in der Bibliothek.
  - Gleichzeitig nur eine Zerlegung je Projekt (409 `studio_decompose_busy`), damit Doppelklicks keine doppelten
    LLM-Kosten erzeugen.
- „Alle Szenen zerlegen“ kommt **nicht** in 2b. Das sind viele LLM-Aufrufe am Stück; besser als Auftrag in Etappe 3.

**Frontend:**
- Storyboard: Karte anklicken → Shot-Formular rechts (Kamera, Beschreibung, Bausteine der Szene, Dauer, Speichern,
  Löschen über Dialog). Pfeile ←/→ auf der Karte ändern die Reihenfolge. „+“ legt einen neuen Shot an.
- Knopf „In Shots zerlegen“ in der Storyboard-Leiste. Er zeigt beim Arbeiten einen Ladezustand und ist dann gesperrt.
  Danach kommt die Rückmeldung „3 Shots angelegt“ oder die Fehlermeldung. Bei vorhandenen Medien öffnet sich der Dialog
  „Ersetzen?“ mit dem Hinweis, dass die Bilder in der Bibliothek bleiben.
- Gesamtdauer der Szene in der Storyboard-Leiste.

**Prüfung wie immer:** Tests rot/grün, Mutanten, Gegenprobe `main`, hydratest-E2E mit echtem Klick auf „In Shots
zerlegen“ (echtes Modell des Testservers; schlägt das fehl, zählt auch die saubere Fehlermeldung), 1600/1280 px,
Bilder direkt im Chat.

## Bauplan Etappe 3 – Erzeugen (17.10.)

**Ist-Stand:** Das Atelier erzeugt Bilder über die Bild-Schnittstelle von OpenRouter (`/api/v1/images`). Seine Stärken
für gleichbleibende Figuren sind Referenzbilder und, bei manchen Modellen, ein Seed. Lokale Workflows laufen über die
Kern-Registry (`local:`). Videos entstehen über `/api/v1/videos` als Image-to-Video aus einem Startbild
(`frame_images`, `first_frame`); das ist ein Hintergrundauftrag mit Abfrage alle 5 s und höchstens 2 Videos
gleichzeitig. Der Kern hat dafür schon Bausteine (`tools/_openrouter_video`: Abfrage + Download;
`llm/media_models.get_media_model`: zentrales Standardmodell je Art; `llm/video_backends`: lokale Workflows).

**Grundsatz:** Das Studio nutzt die **Kern-Bausteine**, nicht Code aus dem Atelier (das Atelier fällt in Etappe 8 weg).
Was im Atelier gut gelöst ist, wird als eigene Kopie übernommen und gekennzeichnet: der Bild-Aufruf mit Referenzen und
die Abfrage-Schleife für Videos. Modell je Art: `models.image` bzw. `models.video` aus dem Drehbuch, sonst das zentrale
Standardmodell des Servers (`get_media_model`). Es stehen keine festen Modelle im Code.

**Aufteilung** (je ein PR, wie bei Etappe 2):
- **3a – Bild für einen Shot:** Im Shot-Formular „Bild erzeugen“. Der Prompt entsteht aus der Beschreibung des Shots,
  den Kamera-Vorgaben der Szene, dem Look des Drehbuchs und dem Aussehen der Bausteine. Die Referenzbilder der Bausteine
  gehen als Referenzen mit. Das Ergebnis landet in `studio/media/images/` mit Begleitdatei (Prompt, Modell,
  Referenzen) und erscheint in der Bibliothek (neue Quelle „Studio“). `image_rel` des Shots wird gesetzt, der Status
  wird `image_ready`.
  - **Varianten:** Jedes neue Bild wird zusätzlich in `shots[].variants[]` (höchstens 8) gemerkt. Im Formular kann man
    zwischen den Varianten wählen; „übernehmen“ setzt `image_rel`.
  - Läuft als **Auftrag im Hintergrund** (ein Bild dauert 10–60 s). Die Anfrage kommt sofort zurück, das Storyboard zeigt
    „läuft“ und fragt alle 3 s nach.
- **3b – Video für einen Shot:** „Video erzeugen“ aus dem gewählten Bild (Image-to-Video), Dauer aus dem Shot und an
  die erlaubten Dauern des Modells angepasst. Ablage in `studio/media/videos/`, `video_rel` wird gesetzt, der Status
  läuft `video_processing` → `done` bzw. `failed`. Höchstens 2 Videos je Server gleichzeitig. Ein Video, das beim
  Neustart des Dienstes mitten im Lauf war, wird beim nächsten Start als `failed` mit verständlichem Hinweis markiert,
  nicht stillschweigend `video_processing` gelassen.
- **3c – Mehrere auf einmal:** Aufträge „Alle Szenen zerlegen“, „Bilder für alle Shots ohne Bild“ und „Videos für alle
  Shots mit Bild“. Sie laufen nacheinander im Hintergrund, mit Fortschritt in der Kopfzeile (die
  „laufen“-Anzeige wird echt), sind abbrechbar und überspringen Fertiges. Vor dem Start nennt ein Dialog die Anzahl und
  die Kosten-Art („N Bilder mit Modell X“). Es gibt keine automatische Kostenschätzung, weil die Preise je Anbieter
  wechseln.
- **3d – Sprache und Musik** (zum Shot bzw. zur Szene): erst nach Etappe 5 „Ton“ sinnvoll, weil es vorher keinen
  Platz dafür auf der Zeitleiste gibt. Verschoben nach Etappe 5.

**Bauplan 3c im Detail (17.10.):**
- Drei Sammelaufträge: `decompose_all` (alle Szenen **ohne** Shots zerlegen), `images_all` (Bild für jeden Shot **ohne** Bild)
  und `videos_all` (Video für jeden Shot **mit** Bild und **ohne** Video). Fertiges wird nie überschrieben; neu zerlegen
  oder ersetzen bleibt Sache des einzelnen Shots bzw. der einzelnen Szene.
- `GET …/plan/batch/{art}` nennt vorher, was passieren würde: Anzahl und Modell (aus dem Drehbuch, sonst der Standard des
  Servers). Bei 0 bietet die Oberfläche nichts an.
- `POST …/plan/batch/{art}` startet. Je Projekt läuft höchstens ein Sammelauftrag (409 `studio_batch_running`). Die Schritte
  laufen **nacheinander** (Videos nutzen trotzdem die Grenze von 2 je Server). Ein Fehler bei einem Schritt bricht den
  Sammelauftrag nicht ab; er zählt als fehlgeschlagen und es geht weiter.
- Fortschritt im Auftrag: `total`, `done`, `failed`, `current` (Name des Shots/der Szene). Die Kopfzeile zeigt ihn
  („Bilder: 3 von 8“).
- `POST …/plan/jobs/{id}/cancel` bricht ab: der laufende Schritt wird noch fertig, danach endet der Auftrag mit Status
  `cancelled`. Was fertig ist, bleibt.
- Nach einem Neustart steht ein unterbrochener Sammelauftrag als `failed`/`interrupted` da (wie in 3a); ein neuer Start
  macht mit dem Rest weiter, weil Fertiges übersprungen wird.

**Aufträge (gemeinsam für 3a–3c):** Datei je Auftrag unter `studio/jobs/<id>.json` (Art, Ziel, Status, Fehler,
Zeitstempel), atomar geschrieben. Ein Auftrag je Shot gleichzeitig; ein zweiter Klick ergibt 409
`studio_job_running`. Fehler der Anbieter erscheinen als klare Meldung am Shot (z. B. kein Schlüssel für OpenRouter →
„Für Bilder ist kein Anbieter eingerichtet. Das geht in der Admin-Konsole unter KI-Modelle.“). Der Text kommt aus den
Übersetzungen, nicht vom Anbieter.

**Sicherheit:** Referenzbilder nur aus dem Projekt (Prüfung wie in 2a). Antworten der Anbieter werden auf Bildart und
Größe geprüft (höchstens 30 MB Bild, 500 MB Video), bevor sie gespeichert werden. Downloads gibt es nur von der Adresse,
die der Anbieter für den Auftrag nennt.

**Prüfung:** wie immer. Für die E2E auf hydratest braucht es einen funktionierenden Bild- bzw. Video-Anbieter
(OpenRouter-Schlüssel). Ohne ihn wird der Fehlerfall geprüft und der Erfolgsfall mit einem lokalen Test-Server, der
eine OpenRouter-kompatible Bild- bzw. Video-Schnittstelle nachstellt (Adresse über die Kern-Einstellung, falls es sie
gibt; sonst nur Tests).

## Nachtrag Reiter (17.10.) – keine Attrappe mehr

**Anlass:** Till hat den Reiter „Erzeugen“ geöffnet und konnte nichts tun. Die rechte Seite war noch die Attrappe aus
Etappe 0: alles gesperrt, dazu der veraltete Text „kommt in Etappe 3“. Erzeugen gab es bisher nur in „Planen“ (Shot
wählen). Ton, Untertitel und Ausgabe zeigten noch die Beispiel-Zeitleiste „Nordwind“. Grundsatz ab jetzt: **Kein Reiter
zeigt Beispieldaten oder gesperrte Attrappen.** Was noch nicht da ist, sagt das ehrlich und führt dorthin, wo es
weitergeht.

- **Erzeugen** nutzt dieselben Daten und Bausteine wie „Planen“:
  - **Links „Shots“:** alle Shots aller Szenen in Drehbuch-Reihenfolge, nach Szene gruppiert, mit kleinem Bild und
    Stand. Der Stand ist einer von „ohne Bild“, „Bild“, „Video“, „läuft“, „fehlgeschlagen“ (aus dem letzten Auftrag des
    Shots).
  - Oben in der Liste stehen die Zahlen „N mit Bild · M mit Video von X“.
  - Ohne Shots erscheint ein Hinweis mit dem Knopf „Zum Planen“.
  - **Mitte:** Bild oder Video des gewählten Shots, wie in „Planen“.
  - **Rechts:** das Shot-Formular mit Bild erzeugen, Varianten und Video erzeugen, wie in „Planen“. Ist kein Shot
    gewählt, steht dort der Hinweis „Wähle links einen Shot“.
  - **Unten:** das Storyboard der Szene des gewählten Shots, mit „Für alle …“. Laufende Sammelaufträge stehen in der
    Kopfzeile.
- **Ton, Untertitel, Ausgabe:**
  - Unten steht statt der Beispiel-Zeitleiste ein ehrlicher Hinweis. Er sagt, was dort kommt (ohne
    Etappen-Nummern), und hat einen Knopf „Zum Schneiden“, um den Film anzusehen.
  - Rechts stehen weiter die Angaben zu einem gewählten Medium der Bibliothek.
- **Beispieldaten entfallen ganz:** `demoData.ts`, die Attrappen-Zeitleiste und das gesperrte Erzeugen-Formular werden
  gelöscht.
- **Prüfung:** Ein Browser-Test öffnet jeden der sechs Reiter. Er prüft, dass nirgends Beispieldaten stehen und dass im
  Reiter „Erzeugen“ ein Bild für einen Shot ohne Bild tatsächlich erzeugt wird (ein Bild, ≈ 1,5 ct).

## Bauplan Etappe 4 – Schneiden (17.10.)

**Ist-Stand:** Die Zeitleiste im Studio ist noch eine Attrappe (`demoData.ts`, Hinweis „Beispiel“). Zoom, Übersichtsleiste,
Zeitmarken, Abspielkopf und die Tastenkürzel-Tabelle gibt es schon (`timeline.ts`, `shortcuts.ts`). Die Bausteine
existieren also: Shots mit Bild bzw. Video und Dauer, Medien in der Bibliothek (Studio-Videos mit `duration`). `ffmpeg`
ist auf jedem Server da, weil Installer und Update es einrichten. Vorbilder: Video-Editor (Proxy, Filmstreifen,
Wellenform) und Kern-Videoschnitt (Abspielen über mehrere Clips). Beides dient nur als Vorlage: eigene Kopien mit
Herkunftsangabe, kein Import über Modulgrenzen.

Wie in Etappe 3 gibt es Schritte. Nach jedem ist etwas Sichtbares fertig:

| Schritt | Inhalt | danach kann man |
|---|---|---|
| **4a** | Schnittfassung als Projektdaten, „Aus dem Drehbuch übernehmen“, echte Zeitleiste im Reiter „Schneiden“, Abspielen des ganzen Films in der Vorschau | den Film zum ersten Mal am Stück ansehen |
| **4b** | Bearbeiten: verschieben, trimmen, teilen (S/Q/W), löschen, verdoppeln, Einrasten, Rückgängig/Wiederholen, Clips aus der Bibliothek auf die Zeitleiste ziehen, automatisch speichern | den Film wirklich schneiden |
| **4c** | Proxies für große Videos (z. B. Uploads aus dem Video-Editor) und Filmstreifen-Vorschau in den Clips | auch lange Videos flüssig schneiden |
| **4d** | Schlichte Filmausgabe: MP4 im Format des Drehbuchs (16:9 → 1280×720, 9:16 → 720×1280, 1:1 → 1080×1080, 25 fps), Originalton der Videos, Stille bei Bildern und Platzhaltern (Platzhalter als schwarze Karte mit Shot-Text), im Hintergrund als Auftrag mit Fortschritt, Ergebnis unter `studio/renders/` und in der Bibliothek | das erste Filmchen als Datei herunterladen |

**4a im Detail**

- **Daten:** Datei `studio/timelines/main.json` (eine Schnittfassung je Projekt; mehrere kommen später, deshalb ein
  Ordner). Die Datei enthält:
  - `revision` (Zähler)
  - `fps` (Standard 25)
  - `tracks`: in 4a eine Videospur `V1`. Der Originalton der Videos gehört zum Clip. Eigene Tonspuren kommen in
    Etappe 5, Text und Untertitel in Etappe 6.
  - Je Clip:
    - `id`
    - `kind` (`video` | `image` | `placeholder`)
    - `start` (Sekunden auf der Zeitleiste)
    - `in`/`out` (Ausschnitt aus dem Medium; bei Bildern 0 bis Dauer)
    - `media_rel` (Pfad relativ zum Projekt, bei Platzhaltern leer)
    - `scene_id`/`shot_id` (Herkunft aus dem Drehbuch, sonst leer)
    - `label`
  - Atomar geschrieben, wie die anderen Studio-Daten.
- **API:**
  - `GET …/timeline`: liefert die Schnittfassung. Ohne Datei kommt eine leere Fassung zurück; dabei wird nichts
    angelegt.
  - `PUT …/timeline`: speichert die ganze Fassung mit der bisherigen `revision`. Weicht sie ab (anderer Tab), kommt
    409 `studio_timeline_conflict`.
  - `POST …/timeline/from-plan`: baut V1 aus dem Drehbuch.
- **Prüfung beim Speichern:**
  - `media_rel` muss eine vorhandene Datei im Projekt mit erlaubter Endung sein, ohne Symlink und ohne `..`.
    Geprüft wird wie in 2a.
  - Zahlen müssen endlich und ≥ 0 sein, `in < out`.
  - Höchstens 2.000 Clips, höchstens 4 Stunden (Konstanten im Modul).
  - Unbekannte Felder werden verworfen.
- **Fehlercodes:**
  - 400 `studio_timeline_invalid`: Fassung verletzt eine Prüfregel. Sie wird ganz abgelehnt, nichts still verworfen
    außer unbekannten Feldern.
  - 409 `studio_timeline_conflict`: `revision` passt nicht.
  - 409 `studio_timeline_not_empty`: Übernahme ohne `replace`, obwohl V1 Clips hat.
  - 400 `studio_timeline_no_shots`: Das Drehbuch hat keine Shots.
- **Medium später gelöscht:** Beim Laden wird ein Clip, dessen Datei fehlt, zum Platzhalter mit `missing: true`.
  Start, Länge, Shot und Name bleiben erhalten. Die Oberfläche zeigt „Medium fehlt“. Der Rest der Fassung bleibt
  unberührt. Einzelne kaputte Clips in der Datei werden beim Laden übersprungen, die Fassung bleibt lesbar.
- **Länge eines Videos** bei der Übernahme: `duration` aus der Begleitdatei des Videos (schreibt 3b mit), sonst die Dauer
  des Shots. Fehlt die Videodatei, wird der Shot als Standbild bzw. Platzhalter übernommen.
- **„Aus dem Drehbuch übernehmen“:**
  - Alle Shots in Drehbuch-Reihenfolge werden lückenlos hintereinander gelegt:
    - Shot mit Video → Videoclip (ganze Länge des Videos)
    - nur mit Bild → Standbild mit der Dauer des Shots
    - ohne beides → Platzhalter mit der Dauer des Shots
  - Ist V1 nicht leer, fragt vorher ein eigener Dialog nach: „Ersetzen“ oder „Abbrechen“. Es gibt kein Browser-Popup.
- **Oberfläche, Reiter „Schneiden“:**
  - Die Zeitleiste zeigt die echte Fassung, der Hinweis „Beispiel“ entfällt. Übersichtsleiste, Zoom und Zeitmarken
    rechnen mit der echten Filmlänge.
  - Leere Fassung: Hinweis mit Knopf „Aus dem Drehbuch übernehmen“.
  - Ein Klick auf einen Clip wählt ihn aus. Rechts erscheinen Art, Quelle, Start, Länge und Shot.
  - Bei Platzhaltern steht dort der Knopf „Im Planen erzeugen“, der direkt zum Shot springt.
- **Abspielen:**
  - Die Vorschau spielt den Film über alle Clips hinweg ab:
    - Videos ab `in`
    - Bilder als Standbild
    - Platzhalter als Karte mit dem Shot-Text
    - Lücken schwarz
  - Eine eigene Uhr (`requestAnimationFrame`) führt. Der nächste Videoclip wird in einem zweiten `<video>`
    vorgeladen, damit es beim Wechsel nicht ruckelt.
  - Leertaste/K, J/L, ←/→, Pos1/Ende und der Zeitcode wirken auf den Film. Klick in die Zeitleiste setzt den
    Abspielkopf.
- **Nicht in 4a:** Bearbeiten (4b), Proxies (4c), Ton- und Textspuren, Übergänge und Export (Etappe 7, siehe offene
  Entscheidung).

**Tests 4a:**

Backend:
- leere Fassung ohne Anlegen
- Speichern und Laden
- `revision`-Konflikt
- jede Prüfregel einzeln
- Übernahme aus dem Drehbuch mit allen drei Clip-Arten, Reihenfolge und Dauer
- nur Projektmitglieder

Frontend:
- Clip-Lage und Länge
- Abspiel-Logik als reine Funktion: welcher Clip bei t, Zeit im Medium, nächster Clip
- Dialog „Ersetzen“
- Platzhalter-Knopf

hydratest-E2E im Testprojekt:
- übernehmen, abspielen über einen Clipwechsel hinweg (Bild → Video)
- Neuladen
- 1600 und 1280 px

## Bauplan 4b – Bearbeiten (17.10.)

**Grundentscheidung: magnetische Hauptspur** (wie CapCut oder die Hauptspur in Final Cut). Die Clips auf V1 liegen
immer lückenlos hintereinander. Verschieben heißt umsortieren. Kürzen, Teilen und Löschen schieben den Rest automatisch
nach. Das passt zu einem Film aus Shots, ist für Laien sofort verständlich und vermeidet Überlappungen und
versehentliche schwarze Lücken. Freies Platzieren mit Lücken und Überlagerungen kommt mit weiteren Spuren (Text, Ton) in
den späteren Etappen.

**Bearbeiten (alles im Browser, reine Funktionen in `cutEdit.ts`, jede Änderung bildgenau auf 1/fps gerundet):**

| Aktion | Bedienung | Wirkung |
|---|---|---|
| Auswählen | Klick auf Clip | wählt ihn aus, Abspielkopf springt an den Anfang |
| Umsortieren | Clip ziehen | Einfügemarke zeigt die neue Stelle, beim Loslassen rückt alles nach |
| Kürzen | linken/rechten Rand ziehen | ändert `in`/`out`, der Rest rückt nach. Mindestlänge 5 Bilder. Videos nicht über ihr Ende hinaus (soweit die Länge bekannt ist) |
| Teilen | S oder Knopf | teilt den Clip unter dem Abspielkopf in zwei |
| Teilen und links/rechts löschen | Q / W | teilt und entfernt den Teil vor bzw. nach dem Abspielkopf |
| Löschen | Entf oder Knopf | entfernt den gewählten Clip, der Rest rückt nach |
| Verdoppeln | Strg+D oder Knopf | Kopie direkt dahinter |
| Kopieren / Einfügen | Strg+C / Strg+V | Einfügen hinter dem gewählten Clip, sonst ans Ende |
| Rückgängig / Wiederholen | Strg+Z / Strg+Shift+Z (oder Knöpfe) | bis 100 Schritte, je Projekt im Browser, nicht gespeichert |
| Einrasten | N oder Magnet-Knopf | beim Kürzen rastet der Rand am Abspielkopf ein |
| Aus der Bibliothek | Video oder Bild auf die Spur ziehen, oder Knopf „An die Zeitleiste anhängen“ in den Eigenschaften | fügt an der Stelle ein. Bilder 5 s, Videos in voller Länge; fehlt die Länge, ermittelt der Browser sie, sonst 5 s. Musik und Sprache gehen noch nicht (Hinweis: kommt mit „Ton“) |

- **Automatisch speichern:** 0,8 s nach der letzten Änderung, mit `revision`.
  - In der Leiste steht der Stand „Gespeichert“, „Speichert …“ oder „Nicht gespeichert“.
  - Bei 409 `studio_timeline_conflict` (anderer Tab) erscheint eine Meldung mit Knopf „Neu laden“. Es wird nichts still
    überschrieben.
  - Verlässt man den Reiter, wird sofort gespeichert.
- **Backend:** zusätzliche Prüfregel: Auf V1 dürfen sich Clips nicht überlappen. Lücken sind erlaubt (ältere Daten).
  Sonst bleibt alles wie in 4a. Ein überlappender Clip lehnt die ganze Fassung ab (400 `studio_timeline_invalid`), beim
  Laden wird der überlappende Clip übersprungen.
- **Tastenkürzel** wirken nur im Reiter „Schneiden“ und nicht in Eingabefeldern. Der Hinweis „kommt mit dem echten
  Schnitt“ entfällt, Marker kommen später („kommt später“).
- **Nicht in 4b:** Proxies und Filmstreifen (4c), MP4-Ausgabe (4d), mehrere Spuren, Übergänge, Mehrfachauswahl.

**Tests 4b:**
- Backend: Überlappung abgelehnt, Lücke erlaubt, beim Laden übersprungen.
- Frontend:
  - jede Bearbeitung als reine Funktion, mit Randfällen: Teilen am Rand, Mindestlänge, Video-Ende, Umsortieren an
    Anfang und Ende, Einfügen aus der Bibliothek
  - Rückgängig und Wiederholen
  - Einrasten
  - Speicherstand und Konflikt
- hydratest-E2E im Browser:
  - Teilen mit S, Umsortieren per Ziehen, Kürzen per Ziehen, Löschen, Verdoppeln
  - Rückgängig und Wiederholen
  - Bild aus der Bibliothek ziehen
  - Neuladen behält alles
  - Konflikt mit zweitem Tab
  - jeweils bei 1600 und 1280 px

## Bauplan 4d – Schlichte Filmausgabe als MP4 (18.10.)

**Ist-Stand (geprüft):**
- Die Schnittfassung `studio/timelines/main.json` hat eine Spur V1 mit Clips der Arten `video`, `image` und
  `placeholder`, jeweils mit `in`/`out`. Lücken zwischen den Clips sind erlaubt.
- `ffmpeg` mit `drawtext` (freetype, fontconfig), `concat`, `color` und `anullsrc` ist auf .2 (8.0) und hydratest
  (6.1) vorhanden. Der Installer richtet es ein (`00-deps.sh`).
- Die Schrift „DejaVu Sans“ wird über `fontconfig-config` (fonts-dejavu-core) immer mitgeliefert.
- Gemessen auf hydratest: 16 s Film aus Video, Standbild und Platzhalter in 0,5 s (`libx264 veryfast`).

**Ablauf:**
- Im Reiter **„Ausgabe“** (bisher „kommt noch“) steht:
  - eine Übersicht: Länge, Zahl der Clips, Format und Größe, Hinweis bei Platzhaltern
  - der Knopf **„Film als MP4 erzeugen“**
  - darunter die Liste der fertigen Filme mit **„Ansehen“** und **„Herunterladen“**
- Der Knopf startet einen Auftrag (wie die Bilder) mit Fortschritt in Prozent. Je Projekt läuft nur ein Film
  gleichzeitig. Kosten entstehen keine, es läuft alles auf dem Server.
- Ergebnis: `studio/renders/<id>.mp4` mit Begleitdatei (Länge, Größe, Revision der Schnittfassung, Zeit). Der Film
  erscheint in der Bibliothek unter der Quelle „Studio · Ausgabe“.

**Was im Film landet:**
- Format nach dem Drehbuch:
  - 16:9 → 1280×720
  - 9:16 → 720×1280
  - 1:1 → 1080×1080
  - 4:3 → 960×720
  - 21:9 → 1680×720
- 25 fps (aus der Schnittfassung), H.264 + AAC 48 kHz Stereo, `+faststart` (im Browser abspielbar).
- **Video-Clip:** Ausschnitt `in`–`out`, eingepasst mit schwarzem Rand (nicht verzerrt, nicht beschnitten),
  Originalton. Hat das Video keinen Ton, entsteht dort Stille.
- **Bild-Clip:** Standbild für die Länge des Clips, eingepasst, Stille.
- **Platzhalter:** schwarze Karte mit dem Clip-Namen (z. B. „Der Sturm · Shot 2“), Stille.
- **Lücke** zwischen Clips: Schwarz und Stille.
- Ein Clip, dessen Datei beim Rendern fehlt, wird zum Platzhalter. Der Film entsteht trotzdem, die Übersicht nennt
  die Zahl.

**Grenzen und Fehler:**
- Leere Zeitleiste: Knopf gesperrt, Hinweis „Erst im Reiter ‚Schneiden‘ Clips anlegen“. Auf dem Server Code
  `studio_render_empty`.
- `ffmpeg` fehlt oder bricht ab: Auftrag `failed` mit Code `render_failed`, die letzten Zeilen des Fehlers stehen
  nur im Log.
- Zeitgrenze: Filmlänge × 4, mindestens 120 s.
- Behalten werden die letzten 10 Filme je Projekt. Ältere werden beim nächsten Rendern gelöscht, nur
  `studio/renders/`.

**Schnittstellen:**
- `POST …/render` liefert den Auftrag (202). Fehler: `studio_render_empty`, `studio_render_running` (409).
- `GET …/renders` liefert die Liste: `rel`, `abs` (für /api/files), Länge, Größe, Zeit.

**Prüfung 4d:**
- pytest:
  - Bau der ffmpeg-Argumente als reine Funktion (Lücke, Bild, Platzhalter, fehlende Datei, Format je
    Seitenverhältnis)
  - echtes ffmpeg-Rendern eines kleinen Films (Länge und Größe mit ffprobe geprüft)
  - Auftrag, nur einer gleichzeitig, leere Zeitleiste, Aufräumen auf 10, Bibliothek, fremdes Projekt 404
- vitest: Reiter „Ausgabe“.
- E2E (nur sichtbare Texte, 1280 und 1600 px): Drehbuch übernehmen, „Film als MP4 erzeugen“, Fortschritt, „Ansehen“
  spielt ab, „Herunterladen“ liefert eine MP4. Länge und Größe der heruntergeladenen Datei mit ffprobe geprüft.

## Etappe B – Bedienbar machen (17.10., vor 4d)

**Anlass (Till, 17.10.):** „Ich habe keine Ahnung, wo ich Bilder erstellen oder Shots hinzufügen kann. Es ist auf das
Sehen ausgelegt, nicht auf das Bedienen. Keine Beschreibungstexte oder Anleitungen.“ Ein Rundgang mit einem leeren
Projekt bestätigt das:
- Das Studio startet in „Schneiden“.
- Leere Flächen sagen „Wähle links …“, obwohl es nichts zu wählen gibt.
- „Szene/Figur/Ort anlegen“ sind nur Symbole ohne Text.
- „Erzeugen“ kann nichts anlegen.
- Die Hilfe ist nur eine Liste der Tastenkürzel, die Kern-Hilfe zur Seite ist leer.

Die E2E-Tests haben über unsichtbare Kennungen geklickt und nie geprüft, ob ein Mensch den Weg findet.

**Grundsätze ab jetzt:**
1. Jede leere Fläche sagt, **was man hier tut**, und bietet den **ersten Schritt als Knopf** an.
2. Wichtige Handlungen sind **beschriftete Knöpfe**, nicht nur Symbole.
3. Jeder Reiter hat oben eine Zeile „Worum es hier geht“, die sich einklappen lässt und gemerkt wird.
4. E2E-Tests für die Bedienung klicken **nur über sichtbare Beschriftungen** (Rolle + Text), nicht über `data-*`.

**Schritte:**

| Schritt | Inhalt |
|---|---|
| **B1** | Geführter Einstieg, beschriftete Knöpfe, Kurzhilfe je Reiter, Fortschrittsleiste, Start im passenden Reiter, Hilfe-Thema „Studio“ |
| **B2** | Drehbuch aus einer Idee (KI) und aus dem **Storyteller** übernehmen |
| **B3** | „Erzeugen“ eigenständig: Shots dort anlegen, **freies Bild** ohne Shot (Prompt, Modell, Format, Galerie) |

**B1 im Detail**
- **Start-Reiter:** Ein Projekt ohne Planung öffnet in „Planen“. Mit Shots, aber ohne Schnittfassung öffnet es in
  „Erzeugen“, sonst in „Schneiden“. Der zuletzt gewählte Reiter je Projekt wird im Browser gemerkt und hat Vorrang.
- **Startfeld in „Planen“**, solange es keine Szene gibt: große Karte „So fängst du an“ mit drei Wegen:
  - **„Aus einer Idee“** (B2): ein bis drei Sätze, die KI schreibt Szenen und Shots.
  - **„Aus dem Storyteller“** (B2): nur wenn das Projekt Bücher hat.
  - **„Selbst anfangen“:** legt die erste Szene an und öffnet sie.

  Dazu kommt, wie bisher, „Aus dem Atelier übernehmen“, falls es dort Daten gibt. Bis B2 fertig ist, sind „Idee“ und
  „Storyteller“ in B1 noch nicht sichtbar. Es gibt keine gesperrten Attrappen (Grundsatz aus dem Reiter-Nachtrag).
- **Beschriftete Knöpfe:**
  - In der Gliederung „+ Szene“, „+ Figur“, „+ Ort“, „+ Gegenstand“ mit Text. Bei 1280 px darf der Text umbrechen.
  - Im Storyboard „+ Shot“ als Knopf in der Leiste, zusätzlich zur Karte.
  - Ist eine Szene ohne Shots gewählt, gibt es zwei große Knöpfe: „Von der KI in Shots zerlegen“ und
    „Shot selbst anlegen“.
- **Kurzhilfe je Reiter** (eine Zeile unter der Kopfzeile, „×“ klappt sie ein, gemerkt im Browser, „?“ holt sie zurück):
  - Planen: „Hier schreibst du dein Drehbuch: Szenen, Figuren und Orte. Zerlege jede Szene in Shots – das sind die
    einzelnen Einstellungen deines Films.“
  - Erzeugen: „Hier entstehen Bilder und Videos. Wähle links einen Shot, erzeuge ein Bild und mach daraus ein Video.
    ‚Für alle …‘ macht das für viele Shots auf einmal.“
  - Schneiden: „Hier setzt du den Film zusammen. ‚Aus dem Drehbuch übernehmen‘ legt alle Shots hintereinander. Ziehen
    sortiert um, die Ränder kürzen, S teilt.“
  - Ton, Untertitel, Ausgabe: der vorhandene „kommt noch“-Text.
- **Fortschrittsleiste** in der Kopfzeile, sobald es Shots gibt:
  - „Shots N · Bilder a/N · Videos b/N · Schnitt ✓/–“.
  - Daneben „Weiter: …“ als Knopf zum nächsten offenen Schritt (Bilder fehlen → Erzeugen, Videos fehlen → Erzeugen,
    kein Schnitt → Schneiden).
- **Leere Flächen:**
  - Mitte in „Planen“ ohne Auswahl, aber mit Szenen: „Klicke links auf eine Szene, um sie zu bearbeiten.“
  - Rechts ohne Auswahl, mit Knopf: „Drehbuch-Kopf bearbeiten“ (Titel, Format, Modelle).
  - Die Texte unterscheiden „noch nichts da“ von „nichts gewählt“.
- **Hilfe:**
  - Das „?“ im Studio öffnet einen Dialog mit zwei Reitern: **„So geht’s“** (kurzer Ablauf in 5 Schritten mit
    Knöpfen, die direkt in den jeweiligen Reiter springen) und „Tastenkürzel“ (wie bisher).
  - Geprüft: Die Hilfe-Themen des Kerns sind eine feste Liste (`HelpTopic` in `i18n/help/loader.ts`), Module können
    keine eigenen hinzufügen. Die Anleitung steht deshalb im Studio-Dialog „So geht’s“, ganz ohne Kern-PR.
- **Übersicht vom Server:** `GET …/projects/{id}/overview` liefert in einem Aufruf:
  - `scenes`, `shots`, `with_image`, `with_video` (Shots mit Bild bzw. Video)
  - `clips` (Clips der Schnittfassung)
  - `atelier` (gibt es übernehmbare Atelier-Daten)

  Nur lesend, nichts wird angelegt. Start-Reiter, Fortschrittsleiste und „Weiter: …“ rechnen daraus, als reine
  Funktion im Frontend.
- **Prüfung B1:** Ein neuer E2E-Test `studio-erstnutzer.cjs` beginnt mit einem leeren Projekt und klickt nur über
  sichtbare Texte (`getByRole(..., { name })`):
  - Start in „Planen“, Startfeld sichtbar
  - „Selbst anfangen“, Szene benennen, speichern
  - „+ Shot“, Beschreibung eintippen, speichern
  - nach „Erzeugen“, Shot anklicken, „Bild erzeugen“ (1 Bild ≈ 1,5 ct)
  - Fortschritt „Bilder 1/1“, „Weiter: Schneiden“
  - „Aus dem Drehbuch übernehmen“, 1 Clip
  - Kurzhilfe ein- und ausklappen, Hilfe „So geht’s“
  - bei 1600 und 1280 px

**B2 im Detail (kurz, eigener Spec-Nachtrag vor dem Bau)**
- **Aus einer Idee:**
  - Eingabe: Idee (bis 2.000 Zeichen), ungefähre Länge (30 s / 1 min / 2 min), Stil (optional).
  - Ein KI-Aufruf mit dem Text-Modell des Drehbuchs erzeugt Titel, Logline, 2–8 Szenen mit Beschreibung, Ort und
    Tageszeit, Figuren mit Aussehen und je Szene 2–5 Shots.
  - Danach eine **Vorschau** mit „Übernehmen“ und „Verwerfen“, nichts wird direkt geschrieben. Übernehmen geht nur in
    ein leeres Drehbuch. Bei vorhandenen Szenen kommt eine Rückfrage „Anhängen“.
- **Aus dem Storyteller:**
  - Die Bücher des Projekts werden aufgelistet (`storyteller/books/*`, nur lesend, eigene Lese-Hilfe mit
    Herkunftsangabe, kein Import über Modulgrenzen).
  - Ein Buch wählen, dann wählen, ob ein oder alle Kapitel übernommen werden.
  - Zuordnung: Kapitel → Szenen-Gruppe, Szene → Szene (Titel, Zusammenfassung → Beschreibung, Perspektive), Steckbriefe
    → Bausteine (Figur/Ort/Gegenstand mit Beschreibung).
  - Optional „gleich in Shots zerlegen“ (Sammelauftrag aus 3c). Auch hier gibt es erst eine Vorschau und dann
    „Übernehmen“.

**B3 im Detail (kurz, eigener Spec-Nachtrag vor dem Bau)**
- In „Erzeugen“ links über der Shot-Liste die Knöpfe „+ Shot“ (Szene wählen) und „Freies Bild“.
- **Freies Bild:** Prompt, Modell (Katalog), Format, Anzahl 1–4, optional Referenzbilder aus der Bibliothek. Die
  Ergebnisse landen in der Bibliothek unter „Studio · frei“ und lassen sich per Knopf einem Shot zuweisen oder auf die
  Zeitleiste legen.

### Bauplan B2 – Drehbuch aus einer Idee und aus dem Storyteller (18.10.)

**Ist-Stand (geprüft):**
- Das Studio hat Kopf, Szenen (mit Shots) und Bausteine. Szenen-Gruppen gibt es nicht.
- Der Regie-Agent (`director.py`) zeigt das Muster für einen KI-Aufruf: Text-Modell aus dem Kopf, sonst das
  Standardmodell, Antwort als JSON, unbrauchbare Antworten werden abgelehnt.
- Storyteller-Format (Modul 0.20.0, nur lesen):
  - `storyteller/books/<id>/book.json` enthält `title`.
  - `structure.json` enthält Teile → Kapitel (`id`, `title`, `scenes`) und Steckbriefe (`kind` character|place|item,
    `name`, `aliases`, `description`, `fields`).
  - `scenes/<id>.json` enthält `title`, `summary` und `pov`.
  - Der Papierkorb liegt außerhalb von `books/`.

**Ein gemeinsamer Entwurf für beide Wege.** Beide Wege liefern einen **Entwurf** und speichern nichts.
- Aufbau:
  - Kopf: Titel, Logline, Beschreibung, Stil
  - Bausteine mit lokalem Schlüssel
  - Szenen mit Beschreibung, Ort, Tageszeit, Bausteinen und Shots
- Der Browser zeigt den Entwurf als Vorschau. Erst „Übernehmen“ schickt ihn zurück. Der Server prüft ihn dann noch
  einmal vollständig (Längen, Arten, Grenzen wie beim normalen Speichern) und schreibt ihn.
- Auf dem Server bleibt kein Entwurf liegen.

**Aus einer Idee:**
- Eingabe:
  - Idee: 1–2.000 Zeichen
  - Länge: „30 s“, „1 min“ oder „2 min“
  - Stil: optional, bis 300 Zeichen
- Ein Aufruf des Text-Modells des Drehbuchs, sonst des Standardmodells. Liefert:
  - Titel und Logline
  - 2–8 Szenen
  - Figuren, Orte und Gegenstände mit Aussehen
  - je Szene 2–5 Shots mit englischem Bild-/Video-Prompt, Einstellung und Dauer (3–10 s)
- Zu viele Szenen oder Shots werden abgeschnitten. Unbekannte Einstellungen werden leer, unbekannte Bausteine fallen weg.
- Unbrauchbare Antwort oder Fehler des Anbieters: Code `studio_idea_failed`, das Drehbuch bleibt unverändert.

**Aus dem Storyteller:**
- Liste der Bücher des Projekts mit Kapiteln und Zahl der Szenen. Nur lesend, eigene Lese-Hilfe, kein Import aus dem
  Storyteller-Modul.
- Ein Buch wählen und Kapitel ankreuzen (Standard: alle). Daraus wird ein Entwurf:
  - Steckbrief → Baustein: character → Figur, place → Ort, item → Gegenstand. Die Beschreibung wird aus `description`
    und den Eigenschaften („Augenfarbe: grün“) zusammengesetzt.
  - Szene → Szene: Titel und Zusammenfassung → Beschreibung. Die Perspektive (`pov`) wird der Szene als Figur
    zugeordnet, wenn sie einem Steckbrief-Namen oder Alias entspricht.
  - Steckbriefe, deren Name oder Alias in Titel oder Zusammenfassung einer Szene vorkommt, werden dieser Szene
    zugeordnet.
  - Kapitel bestimmen nur Auswahl und Reihenfolge. Das Studio hat keine Szenen-Gruppen, der Kapiteltitel geht nicht
    verloren, steht aber nicht in der Szene. **Abweichung von der Kurzfassung oben.**
  - Shots entstehen nicht. In der Vorschau gibt es den Haken „Danach alle Szenen in Shots zerlegen“. Er öffnet nach
    dem Übernehmen den vorhandenen Sammelauftrag-Dialog (3c), mit Anzahl und Modell, vor dem Start.
  - Höchstens 200 Szenen je Entwurf. Was darüber hinausgeht, wird in der Vorschau als Hinweis genannt.
  - Leere Szenen und Szenen ohne Titel bekommen „Szene N“.
  - Kaputte oder fehlende Dateien werden übersprungen, nicht als Fehler gemeldet.

**Übernehmen:**
- Ist das Drehbuch leer, entsteht es aus dem Entwurf („neu“).
- Hat es schon Szenen, werden die neuen Szenen **angehängt**. Die Vorschau sagt das vorher deutlich.
- Bestehende Szenen, Shots und Medien werden nie verändert. Kopf-Felder werden nur gefüllt, wenn sie leer sind.
- Bausteine gleicher Art und gleichen Namens (Groß-/Kleinschreibung egal) werden wiederverwendet, nicht doppelt
  angelegt.

**Wo die Knöpfe sind:**
- Startfeld „So fängst du an“: zusätzlich „Aus einer Idee“ (immer) und „Aus dem Storyteller“ (nur wenn das Projekt
  Bücher hat; `overview.books`).
- Gliederung unter den Szenen: „Szenen aus einer Idee“ und „Aus dem Storyteller“, zum Anhängen.

**Schnittstellen** (alle prüfen die Mitgliedschaft):
- `POST …/plan/draft/idea` mit `{idea, length, style}` liefert `{draft}`.
- `GET …/plan/draft/books` liefert `{books: [{id, title, chapters: [{id, title, scenes}], entities}]}`.
- `POST …/plan/draft/book` mit `{book_id, chapter_ids?}` liefert `{draft, truncated}`.
- `POST …/plan/draft/apply` mit `{draft}` liefert `{mode, scenes, shots, elements_new, elements_reused}`.
- `GET …/overview` bekommt zusätzlich `books` (Anzahl).

**Prüfung B2:**
- pytest: Idee mit ersetztem LLM, Grenzen, kaputte Antwort, Storyteller-Zuordnung, Kapitel-Auswahl, kaputte Dateien,
  neu/anhängen, Wiederverwendung, fremdes Projekt 404.
- vitest: Dialoge und Vorschau.
- E2E (nur sichtbare Texte, 1600 und 1280 px):
  - Leeres Projekt → „Aus einer Idee“ mit echter KI → Vorschau → Übernehmen → Szenen mit Shots.
  - Danach „Aus dem Storyteller“ mit einem Testbuch → angehängt.

### Bauplan B3 – „Erzeugen“ eigenständig: Shot anlegen und freies Bild (18.10.)

**Ist-Stand (geprüft):**
- In „Erzeugen“ zeigt die linke Seite nur die Shot-Liste. Neue Shots gibt es nur in „Planen“.
- Bilder entstehen nur für Shots (`generate._work`, Auftrag je Shot). Die Bibliothek liest `studio/media/images` und
  `studio/media/videos`.
- Shot-Varianten müssen unter `studio/media/images/` liegen (`_clean.shot`).
- Die Zeitleiste hängt Bibliotheks-Bilder bisher nur im Reiter „Schneiden“ an (im Browser, `fromLibrary`, 5 s).

**Links in „Erzeugen“** stehen über der Shot-Liste zwei Knöpfe:
- **„+ Shot“** öffnet eine kleine Liste der Szenen. Ein Klick legt dort einen leeren Shot an und wählt ihn aus. Ohne
  Szenen ist der Knopf gesperrt, der vorhandene Hinweis „Zum Planen“ bleibt.
- **„Freies Bild“** öffnet den Bereich für freie Bilder. Ein Klick auf einen Shot schließt ihn wieder.

**Freies Bild:**
- Rechts steht das Formular:
  - Beschreibung (1–2.000 Zeichen)
  - Modell (Katalog, Standard = Bild-Modell des Drehbuchs bzw. des Servers)
  - Format (Standard = Format des Drehbuchs)
  - Anzahl 1–4
  - optional bis zu 3 Referenzbilder aus der Bibliothek, nur Bilder des Projekts
- Darunter ein Hinweis zu den Kosten: Jedes Bild ist ein Aufruf beim Anbieter.
- Ein Auftrag erzeugt die Bilder nacheinander. Je Projekt läuft nur ein Auftrag für freie Bilder gleichzeitig.
- Der Fortschritt steht im Formular („2 von 4“). Ein fehlgeschlagenes Bild bricht die übrigen nicht ab.
- Die Bilder landen in `studio/media/free/`, jeweils mit Begleitdatei (Beschreibung, Modell, Format, Zeit).
- In der Bibliothek erscheinen sie als Quelle **„Studio · frei“**.
- Die Mitte zeigt die Galerie der freien Bilder, neueste zuerst. Je Bild gibt es:
  - **„Einem Shot zuweisen“**: Auswahl „Szene · Shot N“. Das Bild wird das aktuelle Bild des Shots und eine Variante,
    Status wie beim normalen Erzeugen. Varianten dürfen dafür auch unter `studio/media/free/` liegen.
  - **„Auf die Zeitleiste“**: Das Bild wird als Standbild (5 s) hinten an die Schnittfassung angehängt. Das läuft
    auf dem Server mit Revisionsprüfung, ein offener Schnitt-Tab merkt es beim nächsten Laden.

**Schnittstellen** (alle prüfen die Mitgliedschaft):
- `POST …/plan/free-images` mit `{prompt, model?, aspect_ratio?, count, references?}` liefert den Auftrag (202).
  Fehler: `studio_free_invalid`, `studio_free_running` (409).
- `PUT …/plan/scenes/{sid}/shots/{id}/assign` mit `{image_rel}` liefert den Shot. Erlaubt sind nur echte Bilder
  unter `studio/media/free/` oder `studio/media/images/`. Fehler: `studio_assign_invalid`.
- `POST …/timeline/append` mit `{media_rel}` liefert die Fassung. Erlaubt sind nur Bilder und Videos des Studios
  (`studio/media/…`).

**Prüfung B3:**
- pytest: Auftrag mit ersetztem Anbieter, Anzahl, Referenzen nur aus dem Projekt, ein Fehler je Bild bricht nicht
  ab, Begleitdatei, Bibliothek „frei“, Zuweisen, Anhängen mit Revision, fremdes Projekt 404.
- vitest: Knöpfe links, Formular, Galerie.
- E2E (nur sichtbare Texte, 1280 und 1600 px):
  - „Freies Bild“ mit echtem Bild (≈ 1,5 ct)
  - einem Shot zuweisen
  - auf die Zeitleiste legen
  - „+ Shot“ legt einen Shot in der gewählten Szene an

## Bauplan Etappe 5 – Ton (18.10.)

**Ist-Stand (geprüft):**
- Die Schnittfassung `studio/timelines/main.json` hat nur die Spur `V1` (magnetisch). Ton gibt es nur als Originalton
  der Video-Clips. `clean()` lehnt mehr als eine Spur ab.
- Die Bibliothek zeigt schon Ton (`audio`/`music`) aus Atelier (`atelier/audio`) und Tonstudio (`tonstudio/clips`).
  Zieht man ihn auf die Zeitleiste, kommt der Hinweis „kommt mit ‚Ton‘“ (`cut_no_audio_yet`).
- Die Ausgabe (4d) baut einen concat-Graphen, Ton je Abschnitt ist Originalton oder Stille.
- Der Drehbuch-Kopf hat schon `models.voice` und `models.music` (seit 2a, bisher ungenutzt).
- Kern: Sprache über OpenRouter `/audio/speech` (`media_models.tts`, Stimmen je Modell) oder lokales Piper; Musik
  über OpenRouter (`media_models.music`, Lyria). Schlüssel kommt wie bei Bild/Video über `openrouter_key()`.
- Vorlagen (nur zum Abschauen, eigene Fassung mit Herkunft): Video-Editor `_audio_mix.py` (adelay/volume/afade/amix,
  Stumm/Solo) und `_audio_peaks.py` (Wellenform 60 Werte/s aus PCM).

Wie bisher in Schritten, nach jedem ist etwas Sichtbares fertig:

| Schritt | Inhalt | danach kann man |
|---|---|---|
| **5a** | Tonspuren „Sprache“ und „Musik“ in der Schnittfassung, Ton aus der Bibliothek auf die Spuren ziehen, verschieben, kürzen, teilen, löschen, Wellenform, Abspielen mit Ton, Ausgabe mischt die Tonspuren mit ein | Musik unter den Film legen und als MP4 herunterladen |
| **5b** | Reiter „Ton“: Mixer mit Lautstärke je Spur (auch Originalton), Stumm/Solo, Lautstärke und Ein-/Ausblenden je Clip, Pegelanzeige beim Abspielen | den Ton abmischen |
| **5c** | Sprache und Musik erzeugen (bisher 3d): Sprechtext je Shot → Sprache auf „Sprache“ am Shot-Anfang; Musik für den Film oder eine Szene → „Musik“. Als Auftrag mit Fortschritt, Kosten-Hinweis | den Film ohne fremde Dateien vertonen |

**5a im Detail**

- **Daten:** `tracks` bekommt zwei feste Tonspuren nach `V1`: `A1` (`kind: "audio"`, Name „Sprache“) und `A2`
  (`kind: "audio"`, Name „Musik“). Alte Fassungen ohne Tonspuren werden beim Laden ergänzt, die Datei bleibt
  unverändert, bis der Nutzer speichert. Tonclip: `id`, `kind: "audio"`, `start`, `in`/`out`, `media_rel`, `label`
  (wie Videoclips). Ab 5b zusätzlich `gain_db`, `fade_in`, `fade_out`; je Spur `gain_db`, `mute`, `solo`.
- **Tonspuren sind nicht magnetisch:** Clips liegen frei, Lücken sind Stille. Innerhalb einer Spur dürfen sich Clips
  nicht überlappen (Ablehnen wie bei V1). Verschieben = Ziehen an eine freie Stelle, Einrasten an Clipkanten aller
  Spuren und am Abspielkopf.
- **Ton hängt nicht an den Bildern:** Umsortieren auf V1 verschiebt den Ton nicht. (Die Bindung an einen Shot kommt
  mit 5c, siehe offene Frage.)
- **Prüfung beim Speichern:** wie V1, `media_rel` mit Ton-Endung (`AUDIO_EXT`), höchstens 2.000 Clips über alle Spuren.
  Fehlercodes wie 4a (`studio_timeline_invalid`, `studio_timeline_conflict`). Fehlendes Medium beim Laden → Clip
  bleibt mit `missing: true` und leerem `media_rel` stehen (so wieder speicherbar) und wird als Stille gerendert.
- **Länge eines Tonclips** beim Ablegen: `duration` aus der Begleitdatei, sonst ermittelt der Browser sie, sonst 10 s.
- **Wellenform:** `GET …/waveform?rel=…` rechnet einmal mit ffmpeg (mono, 8 kHz, Spitzenwerte 50 je Sekunde) und legt
  das Ergebnis unter `studio/cache/peaks/` ab (wegwerfbar, Schlüssel = Pfad + Größe + Änderungszeit). Bei Fehler zeigt
  der Clip eine flache Linie, nichts bricht.
- **Abspielen:** Die Vorschau spielt je Tonspur ein eigenes `<audio>` im Takt der Film-Uhr (nachstellen, wenn mehr als
  0,15 s daneben). Originalton der Videos wie bisher.
- **Filmlänge** = Ende des letzten Clips über alle Spuren. Reicht der Ton über das letzte Bild hinaus, wird der Rest
  schwarz (der Ton wird nicht abgeschnitten). Nur Ton ohne Bild ergibt einen schwarzen Film mit Ton.
- **Ausgabe:** Der 4d-Graph liefert Bild + Originalton wie bisher. Danach wird jeder Tonclip mit
  `atrim`/`asetpts`/`adelay` an seine Stelle gelegt und mit dem Originalton per `amix` (`normalize=0`) gemischt,
  zum Schluss `alimiter` gegen Übersteuern. Ohne Tonclips bleibt der Graph genau wie in 4d.
- **Oberfläche (Reiter „Schneiden“):** Unter V1 die Zeilen „Sprache“ und „Musik“. Ziehen aus der Bibliothek legt Ton
  auf die passende Spur (Musik → „Musik“, sonst „Sprache“; Ablegen auf der anderen Spur geht auch). Teilen (S),
  Löschen, Verdoppeln, Rückgängig, Kürzen an den Griffen wirken auf den gewählten Tonclip. Knopf „An die Zeitleiste
  anhängen“ legt Ton ab dem Abspielkopf auf die Spur. Der Hinweis `cut_no_audio_yet` entfällt.

**Tests 5a:**
- pytest: Laden alter Fassung (ergänzt A1/A2), Speichern/Laden mit Tonclips, Überlappung je Spur abgelehnt, Spuren
  ohne Überlappung untereinander erlaubt, falsche Endung, fehlendes Medium, Grenzen; Wellenform (echtes ffmpeg,
  Cache, Pfad außerhalb → 404); Ausgabe: Graph mit/ohne Ton (reine Funktion), echtes Rendern mit Musik (ffprobe:
  Tonspur vorhanden, Länge = Bildlänge).
- vitest: Ablegen, Verschieben mit Einrasten und ohne Überlappung, Teilen/Kürzen, Abspiel-Logik (welcher Tonclip bei
  t, Zeit im Medium).
- E2E (nur sichtbare Texte, 1280 und 1600 px): Musik aus der Bibliothek auf „Musik“ ziehen, verschieben, kürzen,
  abspielen, „Film als MP4 erzeugen“, Download mit ffprobe geprüft (Ton hörbar ≠ Stille per `volumedetect`, Länge =
  Ende des letzten Clips).

### Bauplan 5c – Sprache und Musik erzeugen (18.10.)

**Ist-Stand (geprüft):**
- Shots haben `prompt`, `duration`, Bild und Video, aber keinen Sprechtext. Szenen haben `dialogues` (Sprecher-Baustein,
  Text, Tonfall), die bisher nur der Regie-Agent liest.
- Drehbuch-Kopf: `models.voice` und `models.music` (seit 2a, Auswahllisten aus dem Kern-Katalog).
- Kern: `hydrahive.tools._openrouter_media.synthesize_speech(text, voice, model, key=…)` liefert wav/mp3 (Stimmen je
  Modell über `media_models.voices_for`), `voice.tts.synthesize_local` für lokales Piper (`local/…`). Musik über
  OpenRouter-Chat mit `modalities: [text, audio]` als Stream, gelesen mit `_openrouter_media.read_audio_sse` (wie im
  Atelier). Standard: `media_models.tts` bzw. `media_models.music`. Auf hydratest: `hexgrad/kokoro-82m`, Lyria.

**Was der Nutzer bekommt:**
- **Sprechtext je Shot:** Im Shot-Formular (Planen und Erzeugen) neue Felder **„Sprechtext“** (bis 1.000 Zeichen) und
  **„Stimme“** (Auswahl aus den Stimmen des Sprachmodells, leer = Standard des Modells). Knopf **„Sprache erzeugen“**.
  Das Ergebnis: Datei `studio/media/voice/<id>.wav|mp3` mit Begleitdatei (Text, Stimme, Modell, Dauer, Shot) und
  `voice_rel` am Shot. Kosten-Hinweis vor dem Start (wie bei Bildern: „kostet je nach Modell ein paar Cent“).
- **Sammelauftrag „Sprache für alle Shots mit Sprechtext“** im bestehenden Menü „Für alle …“.
- **Sprache gehört zum Shot** (Till 18.10.): Beim „Aus dem Drehbuch übernehmen“ wird die Sprache eines Shots auf die Spur
  „Sprache“ an den Anfang seines Bildclips gelegt (`shot_id` gesetzt). Beim Umsortieren, Kürzen oder Löschen auf V1
  wandert der gebundene Sprachclip mit: Er beginnt immer am Anfang seines Bildclips, bleibt höchstens so lang wie der
  Bildclip und verschwindet mit ihm. Ein Sprachclip lässt sich lösen („Vom Shot lösen“); dann ist er frei wie in 5a.
  Neu erzeugte Sprache ersetzt die gebundene Sprache des Shots auf der Zeitleiste (vorher Rückfrage im eigenen Dialog,
  falls dort von Hand verändert).
- **Musik erzeugen** im Reiter „Ton“: Knopf **„Musik erzeugen …“** öffnet ein Formular mit Beschreibung (vorbelegt aus
  Stimmung/Look des Drehbuchs bzw. der Szene), Länge (bis 180 s, Standard: Filmlänge bzw. Länge der Szene, sofern das
  Modell das kann), Ziel **„für den ganzen Film“** oder **„für die Szene …“**. Ergebnis `studio/media/music/<id>.mp3` mit
  Begleitdatei; es wird auf die Spur „Musik“ gelegt (ganzer Film: ab 0; Szene: ab dem ersten Clip der Szene) und erscheint
  in der Bibliothek als „Studio · Musik“. Kosten-Hinweis.
- Beides läuft als Auftrag mit Fortschritt (vorhandene `jobs.py`), Fehler mit verständlicher Meldung (kein Schlüssel,
  Anbieter lehnt ab, unlesbare Antwort). Erst wenn ffprobe die Datei als Ton erkennt, wird sie angenommen.

**Prüfregeln:**
- Sprechtext ≤ 1.000 Zeichen, Musikbeschreibung ≤ 2.000, Länge 5–180 s. Stimme muss eine der Stimmen des Modells sein
  (sonst Standard + Hinweis in der Begleitdatei, wie der Kern es tut).
- Höchstens ein Musikauftrag je Projekt gleichzeitig; Sprache bis zu zwei gleichzeitig (wie Videos).

**Tests 5c:**
- pytest (Anbieter gestubbt, kein Netz): Sprache je Shot (Datei, Begleitdatei, `voice_rel`, Fehlerfälle, Stimme), Sammelauftrag,
  Musik (Ziel Film/Szene, Ablage, Bibliothek, Platz auf der Spur), Bindung an den Shot (from-plan legt Sprache an, Umsortieren/
  Kürzen/Löschen auf V1 nimmt sie mit, Lösen), Prüfregeln.
- vitest: Formularfelder, Bindungslogik als reine Funktion, Dialoge.
- E2E auf hydratest mit **echter** Sprache (kokoro, Bruchteil eines Cents) und **echter** Musik (Lyria, ≈ 4 ct je Stück), nur sichtbare
  Texte, 1280 und 1600: Sprechtext eintippen, erzeugen, übernehmen, Sprache liegt am Shot, Umsortieren nimmt sie mit, Musik für den
  Film erzeugen, Film als MP4 mit Sprache und Musik (Pegel per volumedetect).

**Schritte:** 5c-1 Sprache je Shot + Bindung, 5c-2 Musik erzeugen. Ein PR je Schritt.

**Nachtrag 5c-2 – Musik erzeugen (18.10., nach 5c-1):**
- Der Auftrag `music` (höchstens einer je Projekt, sonst 409 `studio_music_running`) erzeugt **nur die Datei**:
  `studio/media/music/<id>.mp3` mit Begleitdatei (Beschreibung, gesendeter Prompt, Modell, Länge, gewünschte Länge,
  Szene, Zeit). In der Bibliothek erscheint sie als „Studio · Musik“ (Art Musik).
- **Auf die Zeitleiste legt sie der Browser**, sobald der Auftrag fertig ist (wie Ablegen aus der Bibliothek, ein
  Verlaufsschritt, automatisch gespeichert). So schreibt weiter nur ein Ort die Schnittfassung; ein Auftrag im
  Hintergrund kann das Speichern des offenen Fensters nicht in einen Konflikt treiben. Ist das Studio beim Fertigwerden
  zu, liegt die Musik in der Bibliothek und kann hineingezogen werden (die Meldung beim Start sagt das).
- Platz: ganzer Film ab 0, Szene ab dem ersten Bildclip der Szene (sonst ab dem Abspielkopf). Ist die Stelle belegt,
  die nächste freie Stelle (wie 5a). Länge: höchstens die gewünschte Länge; wird gekürzt, blendet die Musik die letzten
  2 s aus.
- Formular **„Musik erzeugen …“** im Reiter „Ton“: Beschreibung (vorbelegt aus Look und Logline des Drehbuchs bzw. der
  Beschreibung der Szene), Ziel „Ganzer Film“ oder eine Szene, Länge in Sekunden (5–180, vorbelegt mit der Länge des
  Films bzw. der Szene), Modell (aus dem Drehbuch, sonst Standard des Servers), Kosten-Hinweis (Lyria ≈ 4 ct je Stück).
- Anbieter: OpenRouter-Chat mit `modalities: [text, audio]` als Stream; den Stream liest der Kern
  (`_openrouter_media.read_audio_sse`). Dem Prompt wird „Instrumental, about N seconds long“ angehängt.
- Fehlercodes: `studio_music_needs_text` (400), `studio_not_found` (Szene, 404); im Auftrag `no_key`,
  `provider_rejected`, `provider_unreachable`, `empty_answer`, `bad_audio`.

### Bauplan 5b – Mischpult (18.10.)

**Ist-Stand (nach 5a, geprüft):** Tonspuren `A1`/`A2` mit Clips (`start`, `in`, `out`, `media_rel`). Die Ausgabe mischt
mit `amix normalize=0` + `alimiter`. Der Reiter „Ton“ zeigt noch „kommt noch“. ffmpeg hat `volume`, `afade`, `asplit`,
`sidechaincompress` (8.0 auf .2, 6.1 auf hydratest).

**Daten (Erweiterung der Schnittfassung, alles optional, Standard = heutiges Verhalten):**
- Je Spur `V1`, `A1`, `A2`: `gain_db` (−60 bis +12, Standard 0), `mute` (Standard aus), `solo` (Standard aus). Bei
  `V1` gelten die Werte für den Originalton der Videos.
- Je Tonclip: `gain_db` (−60 bis +12), `fade_in`, `fade_out` (Sekunden, ≥ 0, zusammen höchstens die Cliplänge).
- Fassungsweit `duck`: Musik automatisch leiser, solange auf „Sprache“ etwas klingt (Standard **an** – Till 18.10.:
  „ja“). Gespeichert wird nur `duck: false`.
- Werte, die dem Standard entsprechen, werden nicht gespeichert: alte Fassungen und die Ausgabe ohne Mischpult-Einstellungen
  bleiben genau wie in 5a.
- Ungültige Werte (außerhalb des Bereichs, falscher Typ, Blenden länger als der Clip) werden beim Speichern abgelehnt
  (`studio_timeline_invalid`). Beim Laden einer Datei fallen ungültige Mischpult-Werte still auf den Standard zurück.

**Regeln:**
- Solo: Gibt es mindestens eine Solo-Spur, klingen nur Solo-Spuren. Sonst klingen alle nicht stummen Spuren.
- **Ducking als feste Kurve** (statt Kompressor, damit Vorschau und Film gleich klingen und es exakt prüfbar ist): aus
  den hörbaren Sprachclips entstehen Zeiträume. Die Musik sinkt 0,2 s vor Beginn eines Sprachclips auf −12 dB und kehrt
  nach dessen Ende in 0,6 s zurück (Trapez je Zeitraum, überlappende nehmen das Minimum). Dieselbe Formel rechnet die
  Vorschau (TypeScript) und die Ausgabe (`volume='…':eval=frame`, Python). Höchstens 300 Zeiträume; nahe beieinander
  liegende (Abstand < 0,8 s) werden zusammengelegt.
- Lautstärke und Blenden: Ausgabe exakt (`volume=…dB`, `afade`). Vorschau über Web Audio (je Medium eine
  Verstärkung, je Kanal ein Analyser für die Pegelanzeige), daher auch über 0 dB hinaus. Kann der Browser Web Audio
  nicht starten, bleibt der Ton über die normale Lautstärke des Elements (höchstens 0 dB).

**Oberfläche:**
- Reiter **„Ton“** (bisher „kommt noch“): oben die Vorschau und dieselben Abspielknöpfe wie „Schneiden“, unten das
  **Mischpult** mit drei Kanälen „Originalton“, „Sprache“, „Musik“: Regler (dB, Doppelklick = 0), Knöpfe **Stumm** und
  **Solo**, Pegelanzeige beim Abspielen (Web-Audio-Analyser je Kanal), Zahl der Clips.
- Schalter **„Musik leiser, wenn gesprochen wird“**.
- Rechts die Eigenschaften des gewählten Tonclips: Lautstärke, **Einblenden** und **Ausblenden** (Sekunden).
- Auch im Reiter „Schneiden“ zeigen die Tonclips ihre Blenden als Schräge und die Spurköpfe Stumm/Solo-Zustand.
- Alles läuft über den bestehenden Verlauf (Rückgängig) und das automatische Speichern.

**Tests 5b:**
- pytest: Prüfregeln der neuen Felder, alte Fassungen unverändert, Graph als reine Funktion (Lautstärke je Clip/Spur,
  Blenden, Stumm/Solo, Originalton aus, Ducking nur mit Sprache und Musik), echtes Rendern: stumme Spur still, Solo,
  Lautstärke −20 dB messbar leiser, Blende am Anfang leiser als in der Mitte, Ducking: Musik während Sprache leiser.
  Die Ducking-Kurve ist in Python und TypeScript an denselben Stützstellen gleich (gemeinsame Testtabelle).
- vitest: Mix-Logik (wer klingt, Lautstärke bei t mit Blenden und Ducking), Mischpult, Eigenschaften.
- E2E (nur sichtbare Texte, 1280 und 1600): Musik leiser stellen, Stumm, Solo, Blende setzen, Rückgängig, Neuladen,
  Film erzeugen und Pegel per `volumedetect` prüfen.


## Bauplan Etappe 6 – Untertitel (18.10.)

**Tills Vorgaben (18.10.):** Untertitel **als Dateien, nie eingebrannt** („ich hasse eingebrannte Texte“). Quelle:
Sprechtexte oder Heraushören – „vielleicht beides“ → beide Wege, der Nutzer wählt. Damit entfällt „Einbrennen“ aus
der Etappenliste.

**Ist-Stand (geprüft):**
- Sprechtexte stehen je Shot (`speech`, 5c-1), die erzeugte Sprache liegt als gebundener Clip auf A1 (`shot_id`) am
  Anfang ihres Bildes. Daraus ergeben sich Text **und** Zeit ohne Kosten.
- Kern: Heraushören über OpenRouter `/audio/transcriptions` (`media_models.transcribe` = `openai/whisper-large-v3`) und
  lokal über Wyoming faster-whisper. Der Kern-Baustein `transcribe_file` gibt nur Text zurück, **ohne Zeiten**.
- Probe auf hydratest (18.10.): `response_format=verbose_json` + `timestamp_granularities[]=segment` liefert Abschnitte
  mit `start`/`end` (whisper-large-v3 und whisper-1). Kosten laut Antwort ≈ 0,03 ct je 10 s (≈ 2 ct für 10 min Film).
  **Ohne Sprachangabe erkannte Whisper einen deutschen Clip als Englisch** und lieferte Unsinn → die Sprache wird immer
  mitgeschickt. Lokales Wyoming liefert keine Zeiten → für 6b nur OpenRouter (lokal später, falls Zeiten möglich).

| Schritt | Inhalt | danach kann man |
|---|---|---|
| **6a** | Untertitelspur aus den **Sprechtexten**, Reiter „Untertitel“ (Liste bearbeiten, Spur unter der Zeitleiste, Anzeige in der Vorschau), Herunterladen als **SRT und WebVTT** | Untertitel ohne Kosten als Datei mitgeben |
| **6b** | **Aus dem Ton heraushören** (Auftrag: Ton des fertigen Schnitts mischen → Whisper mit Zeiten), Kosten-Hinweis | auch Originalton und frei gelegte Sprache untertiteln |
| **6c** | **Übersetzen** in weitere Sprachen (Text-KI, Zeiten bleiben), je Sprache eine Datei; in der Ausgabe optional als **abschaltbare** Untertitelspur im MP4 (nicht eingebrannt) | mehrsprachige Untertitel |

**Daten:** `studio/subtitles/<sprache>.json` (z. B. `de.json`): `{language, source: "speech"|"audio"|"translation",
from?, revision, cues: [{id, start, end, text}]}`. Zeiten in Sekunden auf der Film-Uhr, sortiert, ohne Überlappung,
`end - start` ≥ 0,5 s, Text ≤ 2 Zeilen à 42 Zeichen (längere werden beim Erzeugen geteilt), höchstens 5.000 Einträge.
Speichern wie die Schnittfassung mit `revision` (Konflikt → `studio_subtitles_conflict`). Die Sprache des Films steht
im Drehbuch-Kopf (`language`, Standard „de“) und wird dort gewählt.

**6a im Detail**
- **Aus Sprechtexten:** je Shot mit Sprechtext in Reihenfolge der Bildspur. Zeit = gebundener Sprachclip auf A1, sonst
  der Bildclip des Shots auf V1. Text an Satzgrenzen teilen, die Zeit nach Textlänge verteilen; jeder Teil ≤ 7 s.
  Shots, die nicht auf der Zeitleiste liegen, zählen nicht (Hinweis mit Anzahl).
- **Neu erzeugen** über vorhandene, bearbeitete Untertitel fragt in einem eigenen Dialog („Ersetzen“/„Abbrechen“).
- **Reiter „Untertitel“:** links Liste der Einträge (Zeit von/bis, Text), Klick springt in der Vorschau dorthin;
  Text und Zeiten bearbeiten, Eintrag teilen/zusammenführen/löschen/hinzufügen am Abspielkopf; Rückgängig wie im
  Schnitt; automatisch speichern. Unter der Zeitleiste die Zeile „Untertitel“ (Kästchen, Ränder ziehbar).
  Die Vorschau zeigt den aktuellen Untertitel als Überlagerung im Browser (nicht im Bild).
- **Herunterladen:** Knöpfe „SRT herunterladen“ und „WebVTT herunterladen“ (Datei `<Filmtitel>.<sprache>.srt|vtt`);
  die Dateien entstehen beim Abruf aus den Daten, nichts wird doppelt gespeichert.
- **Fehlercodes:** `studio_subtitles_invalid`, `studio_subtitles_conflict`, `studio_subtitles_no_speech` (kein Shot mit
  Sprechtext auf der Zeitleiste), `studio_not_found`.

**Tests 6a:** pytest (Erzeugen aus Sprechtexten mit/ohne Sprachclip, Teilen langer Texte, Reihenfolge nach Umsortieren,
Prüfregeln/Grenzen, Konflikt, SRT/VTT-Format inkl. Zeitformat und Sonderzeichen, nur Mitglieder); vitest (Bearbeiten,
Teilen/Zusammenführen, aktueller Eintrag bei Zeit t, Spur); E2E nur über sichtbare Texte bei 1280 und 1600 px (Erzeugen,
bearbeiten, Rückgängig, Herunterladen und Datei prüfen, nichts im Bild eingebrannt: Film-MP4 unverändert).

### Bauplan 6b – Aus dem Ton heraushören (18.10.)

**Probe auf hydratest (18.10., 15 s Ton mit `language=de`):** whisper-large-v3 liefert je Satz einen Abschnitt, die
Zeiten liegen ≈ 0,3 s neben der echten Stelle, Kosten 0,011 ct (≈ ½ ct je 10 min Film). whisper-large-v3-turbo
ähnlich, etwas ungenauer. whisper-1 fasst alles in **einen** Abschnitt (0–24 s) zusammen → ungeeignet. Lokales
Wyoming liefert keine Zeiten. (Die schlechte Erkennung in der Probe lag an der englischen Testsprecherstimme.)

- **Was gehört wird:** Originalton der Videos (V1) und die Spur „Sprache“ (A1) an ihren Stellen, **ohne Musik** und
  ohne Mischpult-Einstellungen – die Erkennung soll die Stimmen gut hören. ffmpeg mischt das als Mono, 16 kHz, AAC
  32 kbit/s (60 min ≈ 14 MB). Höchstens 60 min Film (`studio_subtitles_too_long`).
- **Auftrag** `transcribe` (Ziel `subtitles:<projekt>:<sprache>`, einer zur Zeit, `studio_subtitles_running`). Modell:
  Standard des Servers für Transkription, wenn er Zeiten je Satz liefert (whisper-large-v3, -turbo). Steht dort ein
  anderes Cloud-Modell (auf hydratest: whisper-1, ein Abschnitt für alles), nimmt das Studio whisper-large-v3 beim selben
  Anbieter; der Dialog zeigt das Modell. Ist ein lokales Modell eingestellt, lehnt der Start ab
  (`studio_subtitles_cloud_model`) – der Ton geht nicht heimlich in die Cloud. Sprache = Sprache des Films, immer mit.
- **Aus den Abschnitten werden Untertitel:** Text gesäubert, Abschnitte mit `no_speech_prob` > 0,6 entfallen,
  lange Abschnitte werden wie in 6a geteilt (Zeilen ≤ 42 Zeichen, ≤ 7 s), Ende höchstens Filmende, keine Überlappung,
  mindestens 0,5 s. Quelle `audio`.
- **Ersetzen:** Vorhandene Untertitel → der Start braucht `replace: true` (sonst `studio_subtitles_not_empty`).
  Ändert jemand die Untertitel, während der Auftrag läuft, schreibt der Auftrag nicht darüber (Fehler `changed`). Im
  Browser ist die Liste währenddessen gesperrt; danach lädt sie den neuen Stand.
- **Oberfläche:** Knopf „Aus dem Ton heraushören …“ → eigener Dialog: Sprache des Films, Länge, Kosten-Hinweis
  („weniger als 1 Cent“ bzw. „etwa N Cent“), Hinweis „Musik wird nicht mitgehört“, bei vorhandenen Untertiteln
  „ersetzt die N Untertitel“. Fortschritt „Ton wird angehört …“, Fehler mit Text.
- **Fehlercodes im Auftrag:** `no_key`, `provider_rejected`, `provider_unreachable`, `empty_answer`,
  `no_speech_found` (kein Abschnitt mit Sprache), `render_failed` (Ton mischen), `changed`.
  Vor dem Start: `studio_subtitles_no_audio` (weder Video noch Sprachclip auf der Zeitleiste).

## Grundregeln (wie immer)

- Alles über die Oberfläche bzw. Admin-Konsole, kein Terminal. UI-Texte ohne Datei- oder Terminal-Hinweise.
- Bestehende Installationen ändern sich durch ein Update nicht, solange der Nutzer nichts auslöst. Die alten Module
  laufen weiter, bis Etappe 8 durch ist.
- Dateien unter ca. 200 Zeilen, Tests nach Thema, keine festen Werte, Fehler über `coded()`.
- Keine `confirm()`-Popups. Gefährliches läuft über einen eigenen Dialog.
- Übernommene Ideen aus Apache-2.0-Projekten (OpenCreator) werden mit Herkunft gekennzeichnet, die Lizenz liegt bei,
  falls Code oder Prompts übernommen werden.

## Offene Punkte (Till)

- ~~Etappe 5~~ → **freigegeben (Till, 18.10.):** Aufteilung 5a/5b/5c. Zwei **feste** Tonspuren „Sprache“ und „Musik“.
  Sprache aus 5c hängt am Shot und wandert beim Umsortieren mit. Musik wird automatisch leiser, wenn gesprochen wird
  (in 5b). Eigenen Ton hochladen kommt mit Etappe 7.

- ~~Bedienbarkeit~~ → **Etappe B vor 4d** (Till, 17.10.). Drehbuch aus einer Idee: ja. Drehbuch aus dem
  **Storyteller** übernehmen: ja („das ideale Drehbuch-Werkzeug, und der ist schon fertig“).

- ~~Etappe 4~~ → **freigegeben (Till, 17.10.): „wie es technisch am besten ist“.**
  - Aufteilung 4a/4b/4c wie oben.
  - **4d** (schlichte MP4-Ausgabe) wird vorgezogen. Die volle Ausgabe mit Vorlagen und Warteschlange bleibt Etappe 7.
  - Bild-Shots kommen als **Standbild** auf die Zeitleiste.
  - Zunächst **eine** Schnittfassung je Projekt (`timelines/main.json`).

- ~~Name im Menü~~ → **„Studio“** (Till, 15.10.).
- ~~Reihenfolge~~ → **Ablauf einer Produktion** (Till, 15.10.): Entwicklung/Vorproduktion → Produktion → Postproduktion →
  Auslieferung, also Planen → Erzeugen → Schneiden → Ton → Untertitel → Ausgabe. Das Meistgenutzte (Atelier, 18
  Projekte auf Prod) kommt zuerst. Schnitt und Export laufen bis Etappe 7 weiter in den alten Modulen.
