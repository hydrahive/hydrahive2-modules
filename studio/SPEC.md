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
| 3 | **Erzeugen:** Bild, Video, Sprache, Musik im Panel, Platzhalter aus dem Drehbuch füllen, Varianten, Ergebnis direkt in der Bibliothek | Vom Drehbuch zu fertigen Shots |
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

## Grundregeln (wie immer)

- Alles über die Oberfläche bzw. Admin-Konsole, kein Terminal. UI-Texte ohne Datei- oder Terminal-Hinweise.
- Bestehende Installationen ändern sich durch ein Update nicht, solange der Nutzer nichts auslöst. Die alten Module
  laufen weiter, bis Etappe 8 durch ist.
- Dateien unter ca. 200 Zeilen, Tests nach Thema, keine festen Werte, Fehler über `coded()`.
- Keine `confirm()`-Popups. Gefährliches läuft über einen eigenen Dialog.
- Übernommene Ideen aus Apache-2.0-Projekten (OpenCreator) werden mit Herkunft gekennzeichnet, die Lizenz liegt bei,
  falls Code oder Prompts übernommen werden.

## Offene Punkte (Till)

- ~~Name im Menü~~ → **„Studio“** (Till, 15.10.).
- ~~Reihenfolge~~ → **Ablauf einer Produktion** (Till, 15.10.): Entwicklung/Vorproduktion → Produktion → Postproduktion →
  Auslieferung, also Planen → Erzeugen → Schneiden → Ton → Untertitel → Ausgabe. Das Meistgenutzte (Atelier, 18
  Projekte auf Prod) kommt zuerst. Schnitt und Export laufen bis Etappe 7 weiter in den alten Modulen.
