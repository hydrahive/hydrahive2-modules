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
| 6 | Untertitel: Transkribieren, Spur, Stil, Übersetzen, zweisprachig, SRT, Einbrennen | Untertitel und Übersetzung |
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
  - Hilfe-Text für die Kern-„Hilfe zur Seite“ nur, wenn der Kern Modul-Themen erlaubt (wird geprüft). Sonst steht er
    im Studio-Dialog, damit es keinen Kern-PR braucht.
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

## Grundregeln (wie immer)

- Alles über die Oberfläche bzw. Admin-Konsole, kein Terminal. UI-Texte ohne Datei- oder Terminal-Hinweise.
- Bestehende Installationen ändern sich durch ein Update nicht, solange der Nutzer nichts auslöst. Die alten Module
  laufen weiter, bis Etappe 8 durch ist.
- Dateien unter ca. 200 Zeilen, Tests nach Thema, keine festen Werte, Fehler über `coded()`.
- Keine `confirm()`-Popups. Gefährliches läuft über einen eigenen Dialog.
- Übernommene Ideen aus Apache-2.0-Projekten (OpenCreator) werden mit Herkunft gekennzeichnet, die Lizenz liegt bei,
  falls Code oder Prompts übernommen werden.

## Offene Punkte (Till)

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
