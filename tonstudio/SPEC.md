# Tonstudio – Spec

Status: **FREIGEGEBEN** durch Till (11.10.2026), Umsetzung ab M1.
Stand: 11.10.2026. Bezug: Tasks `ae837ea0` (Konzept Musikstudio) und `b7b6139a` (Media-Studio, Dach).

---

## 1. Was

Ein HydraHive-Modul **Tonstudio** (Modul-ID `tonstudio`, Name: Entscheidung Till 11.10., gleicher Name wie die App in HydraVR; diese kann das Modul später als Datenquelle nutzen), in dem man **Songs mit KI erzeugt, arrangiert, mischt und exportiert**,
gemeinsam mit den Agenten. Kernarbeit (Entscheidung Till 11.10.: Variante **a**): KI-Clips erzeugen,
auf Spuren anordnen, nach Abschnitten arrangieren, mischen, Mixdown. **Kein** Einspielen per Mikrofon
oder MIDI, **keine** virtuellen Instrumente (siehe §9).

Von Anfang an vorbereitet für zwei spätere Anbindungen (Vorgabe Till):
1. **Media-Studio** (`b7b6139a`): soll Songs und deren Spuren übernehmen können, ohne Umbau.
2. **Autorensystem für Liedtexte** (Storyteller): Liedtexte sollen dort geschrieben und ins Studio
   übernommen werden können.
3. **Notenübergabe** (Till 11.10.): Notenvorlagen als **MusicXML** oder **MIDI** übergeben, zusammen mit
   Liedtexten (§5.4).
4. **Referenzen** (Till 11.10.): Bilder und Audiodateien als Vorlage bzw. Inspiration (§5.5).

## 2. Warum

Heute ist Musik auf vier Stellen verteilt, keine davon ist ein Studio:

| Ort | Kann | Fehlt |
|---|---|---|
| Atelier, Tab Audio (`music.py`, `audio_profiles.py`) | Lyria-Track erzeugen, Sound-Profile, Stil-Anker | Spuren, Arrangement, Mischen |
| Video-Editor, Audio (`SPEC-AUDIO.md`, `_audio_mix.py`) | Mehrspur mit Gain, Fades und ffmpeg-Mix | ist an ein Video gebunden, keine Song-Struktur |
| HydraVR, App „Tonstudio“ (Quest-App, nicht dieses Modul) | Mischpult mit Panorama, Mute und Solo | nur in der Brille, keine Bearbeitung |
| Werkzeug `generate_music` | einzelner Track im Chat | kein Projekt, keine Versionen |

Till 29.09.: „ein wenig mehr in die professionelle Richtung“. Ein eigenes Studio bündelt das, ohne die
anderen Module zu verbiegen.

## 3. Entscheidungen

| # | Entscheidung | Begründung |
|---|---|---|
| E1 | **Eigenes Modul** `tonstudio`, nicht im Atelier | Das Atelier (1.6.6) ist schon groß. Eine Mehrspur-Oberfläche dort ließe sich später kaum ins Media-Studio herauslösen. |
| E2 | **Drei feste Übergaben** von Anfang an (§5): Song-Format, Liedtext-Verweis, Export-Paket | Das Media-Studio und der Storyteller hängen sich später an diese Übergaben, ohne dass das Studio umgebaut werden muss. |
| E3 | **Spur- und Clip-Felder gleich wie im Video-Editor** (`t_start`, `src_start`, `src_end`, `gain_db`, `fade_in`, `fade_out`, `mute`, `solo`) | Gleiche Sprache für Zeitachsen. Das Media-Studio kann eine Song-Timeline direkt als Audiospuren übernehmen. |
| E4 | **Dateibasiert im Projektordner** (`<workspace>/tonstudio/`), wie Atelier und Storyteller | Sichtbar über Samba und Git, Sicherung inklusive, kein Datenbank-Silo. |
| E5 | **Musik-Anbieter austauschbar** (Adapter je Anbieter, §5.6). Lyria über OpenRouter ist nur der Start. | Till 11.10.: „in den Modellen flexibel sein“. Kein Anbieter ist in allem vorn (eigener Text, Audio-Referenz, Länge, Lizenz, lokal). |
| E6 | **Nicht-destruktiv:** Quellen werden nie verändert. Schnitt, Gain und Fades stehen nur im Song. Gerendert wird erst beim Mixdown. | Jede Version bleibt wiederherstellbar, Agenten können nichts kaputt rendern. |
| E7 | **Agenten arbeiten über Vorschläge**, wie im Storyteller | Ein Agent ändert den Song nicht still. Der Mensch übernimmt oder verwirft. Kosten werden vor dem Erzeugen angezeigt. |

## 4. Begriffe und Datenmodell

```
<workspace>/tonstudio/
  songs/<song_id>/
    song.json            Song-Projekt (Format §5.1, versioniert)
    lyrics.md            Liedtext, solange kein Verweis gesetzt ist (§5.2)
    versions/<n>.json    frühere Stände von song.json (Schnappschuss je Speichern mit Änderung)
    exports/<export_id>/ Export-Paket (§5.3)
  scores/<score_id>.musicxml|.mid   Notenvorlagen (unveränderlich, Versionen wie Clips)
  scores/<score_id>.json            Sidecar: Format, Titel, ausgelesene Eckdaten (§5.4), Herkunft
  clips/<clip_id>.mp3    erzeugte oder importierte Audio-Quellen (unveränderlich)
  clips/<clip_id>.json   Sidecar: Herkunft (Modell, Prompt, Liedtext-Version, Kosten, Zeit), Dauer, Peaks-Pfad
  peaks/<hash>.json      Wellenform, aus der Quelle berechnet (Cache, nicht im Song)
```

- **Song:** Tempo, Tonart, Taktart, Abschnitte, Spuren, Master-Einstellungen.
- **Abschnitt** (Intro, Verse, Chorus, Bridge, Outro …): benannter Bereich auf der Zeitachse. Er dient
  dem Arrangement und als Zuordnung zu den Abschnitten im Liedtext.
- **Spur:** Name, Rolle (`full`, `vocals`, `drums`, `bass`, `other`, `fx`), Gain, Panorama, Mute, Solo, Clips.
- **Clip:** Verweis auf eine Quelle (`source_rel`) mit Ausschnitt und Position, Gain und Fades.
- **Quelle:** eine Audiodatei im Projekt. Erzeugt (Lyria), aus dem Atelier, aus `generated/` oder importiert.

## 5. Die drei Übergaben (Kern der Zukunftsfähigkeit)

### 5.1 Song-Format `song.json`

```jsonc
{
  "format": "hydrahive.song",
  "format_version": 1,
  "id": "…", "title": "Die Klans V", "version": 7,
  "bpm": 132, "key": "D minor", "time_signature": "4/4",
  "sections": [ { "id": "s1", "name": "Intro", "kind": "intro", "t_start": 0.0, "t_end": 16.0, "lyrics_section": "intro" } ],
  "tracks": [
    { "id": "t1", "name": "Full Mix", "role": "full", "gain_db": 0, "pan": 0.0, "mute": false, "solo": false,
      "clips": [ { "id": "c1", "source_rel": "tonstudio/clips/ab12.mp3",
                   "t_start": 0.0, "src_start": 0.0, "src_end": 32.0, "gain_db": 0, "fade_in": 0.5, "fade_out": 2.0 } ] }
  ],
  "master": { "gain_db": 0, "loudness_lufs": -14 },
  "lyrics": { "ref": null },
  "score": { "ref": null }
}
```

Regeln:
- `format` und `format_version` sind Pflicht. Ein Leser lehnt Versionen ab, die er nicht kennt, statt
  zu raten. Neue Felder sind optional. Alte Songs bleiben gültig.
- Die Clip- und Spurfelder heißen **genau wie im Video-Editor** (E3). Neu sind nur `pan` und `role`.
  Das Media-Studio übernimmt eine Spur, indem es Felder kopiert, nicht übersetzt.
- `version` steigt bei jedem Speichern. Schreiben mit veralteter Version gibt **409** (kein stilles
  Überschreiben, wie im Storyteller).

### 5.2 Liedtext-Verweis

```jsonc
"lyrics": { "ref": null }                                   // M3: Text liegt in songs/<id>/lyrics.md
"lyrics": { "ref": { "provider": "storyteller", "book_id": "…", "version": 12 } }   // M6: Text kommt aus dem Storyteller
```

- **Format des Textes** (beide Fälle gleich): Markdown mit Abschnitt-Markern, die Lyria 3.5 direkt
  versteht, z. B. `[Intro]`, `[Verse 1]`, `[Chorus]`, `[Bridge]`, `[Outro]`. Klammern `( … )` stehen für
  Hintergrundgesang. Quelle: Google, Lyria-Prompt-Guide, Abschnitt „Lyrics and vocals“
  (https://ai.google.dev/gemini-api/docs/lyria-prompt-guide, gelesen 11.10.2026).
- Ein Abschnitt im Song (`sections[].lyrics_section`) zeigt auf einen Marker im Text. Mit dieser
  Zuordnung kann das Studio später „nur den Refrain neu erzeugen“.
- Jeder erzeugte Clip merkt sich in seinem Sidecar, **welche Textversion** gesungen wurde (Provenienz).
- **M6 Storyteller:** neue Buch-Art `song` (heute `novel`, `story`, `nonfiction`, `learning`). Kapitel
  sind die Songs eines Albums, Szenen die Abschnitte. Das Studio liest den Text über eine Lese-Schnittstelle
  des Storytellers. Änderungen aus dem Studio gehen **als Vorschlag** zurück, nie direkt (Storyteller-Prinzip).
  Ist der Storyteller nicht installiert, bleibt der Text im Studio. Das Studio funktioniert ohne ihn.

### 5.3 Export-Paket

```
exports/<export_id>/
  manifest.json      { format: "hydrahive.song-export", format_version: 1, song_id, song_version,
                       bpm, key, duration, loudness, files: [...], sections: [...], lyrics_version }
  mix.wav | mix.mp3  Mixdown (Master)
  stems/<track>.wav  je Spur einzeln gerendert (gleiche Länge, Startpunkt 0)
  lyrics.md          Liedtext in der gesungenen Version
  score.musicxml|.mid  Notenvorlage, falls vorhanden (§5.4)
  markers.json       Abschnitte mit Zeiten (für Video-Schnitt: Schnitt auf den Refrain)
```

- Das Media-Studio und der Video-Editor importieren **dieses Paket**, nicht die interne Song-Datei.
  Damit bleibt das Studio intern frei.
- Stems sind bis M5 die **gerenderten Spuren**. Ab M5 können zusätzlich aus einem fertigen Clip
  zerlegte Stems (Gesang, Schlagzeug, Bass, Rest) entstehen. Das Paketformat bleibt gleich.

### 5.4 Notenübergabe (MusicXML, MIDI)

```jsonc
"score": { "ref": null }                                                         // keine Noten
"score": { "ref": "tonstudio/scores/<id>.musicxml", "format": "musicxml", "version": 3 }
"score": { "ref": { "provider": "storyteller", "book_id": "…", "version": 4 } }   // M6, wie beim Liedtext
```

**Wichtig – ehrlich:** Lyria liest **keine Noten**. Die Modelle nehmen nur Text und Bilder an (OpenRouter
`/api/v1/models`, `input_modalities: text, image`, geprüft 11.10.). Eine Notenvorlage wirkt deshalb auf zwei Wegen:

1. **Als genauere Beschreibung für Lyria:** Beim Import liest das Tonstudio mit `music21` (BSD-3-Clause) die
   Eckdaten aus: Tonart, Tempo, Taktart, Länge, Abschnitte (Proben-Marken), Akkordfolge je Abschnitt,
   Tonumfang und Verlauf der Melodie. Daraus entsteht Text für den Prompt. Lyria hält sich an Tempo,
   Tonart und Stimmung, **spielt die Melodie aber nicht notengetreu**.
2. **Als notengetreue Vorlage-Spur:** Aus MIDI bzw. MusicXML wird mit **FluidSynth** und der Soundfont
   **FluidR3 GM** (`fluid-soundfont-gm`) Audio gerendert, wahlweise pro Stimme oder Instrument eine Spur.
   Die Spur klingt nach einfachem Synthesizer, ist aber **exakt die Vorlage**, zum Beispiel als
   Führungsstimme, Bass oder Klick-Ersatz unter dem KI-Song. Rolle der Spur: `guide`.

Weitere Regeln:
- **Liedtext aus den Noten:** Enthält die MusicXML-Datei Text unter den Noten, wird er als Liedtext
  übernommen (Abschnitte aus den Proben-Marken). Eine Datei liefert dann beides. Gibt es schon einen
  Liedtext, wird gefragt, statt zu überschreiben.
- **Abschnitte:** Proben-Marken der Noten (A, B, „Refrain“ …) werden auf die Song-Abschnitte abgebildet,
  genau wie die Marker im Liedtext. Mit Tempo und Taktart lässt sich jeder Abschnitt in Sekunden umrechnen,
  das Raster der Zeitachse kommt dann aus den Noten.
- **Anzeige:** Noten im Browser mit OpenSheetMusicDisplay (BSD-3-Clause, MusicXML). MIDI ohne Notenbild
  als Klavierrolle (`@tonejs/midi`, MIT).
- **Formate:** `.musicxml`, `.xml`, `.mxl` (komprimiert), `.mid`, `.midi`. Größengrenze 10 MB.
  Geprüft wird beim Hochladen (Parser), nicht nur die Endung. **Nicht:** Notenbilder oder PDFs lesen
  (Notenerkennung wäre Audiveris, Java und AGPL-3.0, passt nicht hinein).
- **Systempakete** (Till 11.10.: über das Installskript):
  - Kern-PR, getrennt vom Modul, erst mit M3b. `installer/modules/00-deps.sh` installiert
    `fluidsynth fluid-soundfont-gm` mit **`--no-install-recommends`**. Ohne den Schalter käme `qsynth`
    (Qt-Oberfläche) mit, auf einem Server unnötig (apt-Simulation auf .2, 11.10.).
  - `update.sh` holt die Pakete einmalig nach, nach demselben Muster wie ffmpeg und sshpass.
  - Mac: `brew install fluid-synth`, die Soundfont gesondert. Das wird bei M3b geklärt.
  - Der FluidSynth-Dienst des Pakets wird von Debian nicht aktiviert (`dh_installsystemduser --no-enable`).
    Wir rufen nur `fluidsynth -ni -F <wav> <soundfont> <midi>` als Einzelaufruf auf.
  - Platz: Soundfont ~142 MB, FluidSynth unter 1 MB.
  - **Das Tonstudio verlässt sich nicht darauf:** Fehlen FluidSynth oder die Soundfont, zeigt es „Vorlage-Spur
    nicht verfügbar“. Import, Anzeige und Prompt-Übernahme laufen trotzdem.
  - `music21` kommt als Python-Abhängigkeit des Moduls dazu, nicht in den Kern.
- **Export-Paket:** Die Notenvorlage liegt als `score.musicxml`/`score.mid` mit im Paket (§5.3), mit Version.

### 5.5 Referenzen: Bilder und Audiodateien

**Bilder** (Foto, Albumcover, Stimmungsbild): Lyria nimmt Bilder als Eingabe an (OpenRouter
`input_modalities: text, image` für `lyria-3-pro-preview` und `-clip-preview`; Google-Doku: bis zu 10 Bilder,
„compose music inspired by the visual content“, geprüft 11.10.). Das Bild geht direkt mit in den Auftrag.
Die Wirkung ist **Inspiration** (Stimmung, Farben), keine Vorgabe.

**Audiodateien** (MP3, WAV, FLAC, OGG, M4A): Lyria nimmt **kein Audio** an (Google-Doku: „multimodal inputs
(text and images)“, OpenRouter wie oben). Ein „klingt wie diese Datei“ oder „mach weiter“ direkt im
Modell geht also **nicht**. Eine Audiodatei hat im Tonstudio vier Wege:

| Weg | Was passiert | Womit | Etappe |
|---|---|---|---|
| **Als Clip** | Datei liegt in der Bibliothek und kommt auf eine Spur (eigene Aufnahme, Loop, Sample, fertiger Song) | Import + `ffprobe` | M1 |
| **Messen** | Tempo (BPM), Taktschläge, vermutete Tonart, Länge. Das Raster der Zeitachse richtet sich danach. | `librosa` (ISC-Lizenz), lokal | M2 |
| **Als Referenz beschreiben** | Ein Audio-fähiges Modell hört die Datei und beschreibt Genre, Instrumente, Gesang, Aufbau und Stimmung als Text. Der Text wird **sichtbar** und änderbar in den Lyria-Prompt übernommen („im Stil der Referenz“). | Gemini Flash über OpenRouter (`input: audio`, Ausgabe Text) | M3c |
| **Text heraushören** | Gesungenen Text als Liedtext-Entwurf übernehmen | Whisper (lokal, `local/whisper`, schon vorhanden) | M3c |
| **In Spuren zerlegen** | Gesang, Schlagzeug, Bass und Rest als eigene Quellen | Demucs (MIT-Lizenz), lokal auf der GPU | M5 |

Regeln:
- Die Referenz-Beschreibung ist ein **Text, den man sieht**. Kein verdeckter Datei-Upload an Lyria. Im Sidecar
  des Clips steht, welche Referenz verwendet wurde (Provenienz).
- Fremde Audiodateien bleiben im Projekt. Nur bei „beschreiben“ geht die Datei an den Cloud-Anbieter. Das wird
  vorher angezeigt, mit den Kosten. „Messen“, „Text heraushören“ und „Zerlegen“ laufen lokal.
- Hinweis in der Oberfläche: Bei fremden Songs liegen die Rechte bei den Urhebern. Die Referenz beschreibt den
  Stil, sie kopiert nichts. Für Veröffentlichungen gilt das Recht des Nutzers.
- Upload-Grenze für Audio wie §8 (100 MB), Prüfung mit `ffprobe`.

### 5.6 Musik-Anbieter (austauschbar)

**Prinzip:** Das Tonstudio kennt **keinen festen Anbieter**. Jeder Anbieter ist ein Adapter mit derselben
Schnittstelle (Muster wie `llm/video_backends`: `list_models`, `submit`, `poll`, `fetch_output`). Er meldet,
was er kann. Die Oberfläche zeigt nur die Möglichkeiten, die das gewählte Modell hat.

```jsonc
// was ein Adapter je Modell meldet (Beispiel)
{ "id": "elevenlabs:music_v2_5", "name": "Eleven Music v2.5", "backend": "elevenlabs",
  "lyrics": true, "instrumental_switch": true, "image_ref": false, "audio_ref": true,
  "sections": true, "inpaint": true, "max_seconds": 300, "price": { "per_minute_usd": 0.15 },
  "license_note": "kommerziell ab Starter-Plan (Anbieter-Bedingungen)", "local": false }
```

Der Auftrag ist anbieterneutral: Stil-Prompt, Liedtext mit Abschnitt-Markern, Länge, BPM, Tonart, Referenzen
(Bilder, Audio, Noten-Eckdaten). Kann ein Modell etwas nicht, wird es **nicht still weggelassen**: Es steht als
Hinweis am Auftrag („Audio-Referenz wird bei Lyria als Beschreibung übergeben“, §5.5).

**Kandidaten** (geprüft 11.10.2026 auf den offiziellen Seiten; Preise und Bedingungen vor dem Einbau erneut prüfen):

| Anbieter / Modell | Zugang | Eigener Text | Audio-Referenz | Länge | Lizenz / Preis | Bemerkung |
|---|---|---|---|---|---|---|
| **Google Lyria 3 Pro / Clip** | OpenRouter (heute schon in HydraHive) | ja (`Lyrics:` + Marker) | nein (nur Text + Bild) | Pro ~2–3 min, Clip 30 s | OpenRouter meldet Preis 0, **unklar** (§10) | Start-Anbieter, Bild-Referenz |
| **Google Lyria 3.5** | Gemini API (eigener Google-Schlüssel), bei OpenRouter noch nicht | ja | nein (Text + bis 10 Bilder) | „a couple of minutes“, über Prompt steuerbar | Google-Preisliste | gibt Text und Song-Struktur zurück |
| **ElevenLabs Eleven Music v2 / v2.5** | eigene API (`model_id=music_v2_5`), Schlüssel im Credential-Store | ja, auch **Composition Plan** (Abschnitte einzeln) | **ja** („Audio Reference“) | 3 s – 5 min (Doku), API-Feld bis 600.000 ms | **0,15 USD/min** (API-Preisliste); „cleared for nearly all commercial uses“, kommerziell ab Starter-Plan | Abschnitte einzeln neu erzeugen (Inpainting), `force_instrumental` |
| **Stability Stable Audio 2.5** | Stability-API, fal, Replicate, ComfyUI | Gesang **nicht** belegt (eher Instrumental, Sound) | **ja** (Audio-zu-Audio, Inpainting: „input their own audio … generate the rest“) | bis 3 min | Bedingungen von Stability | gut für Instrumental, Loops, Fortsetzen |
| **MiniMax Music 3.0** | MiniMax-API | ja (`lyrics`, Marker `[Verse]`, `[Chorus]`) | **ja** (Cover einer Vorlage) | – | Laut Doku für **neue** Nutzer derzeit gesperrt, freie Varianten werden eingestellt | Offene Gewichte auf Hugging Face (`MiniMaxAI/MiniMax-Music3`, Lizenz nicht angegeben → prüfen) |
| **ACE-Step 1.5** (offen) | **lokal**, eigener REST-Server (`acestep-api`), ComfyUI-Knoten | ja, 50+ Sprachen | **ja** (Referenz, Cover, Repaint) | 10 s – 10 min | **MIT** (Repo, Hugging Face) | Kein Cloud-Aufruf, keine Kosten je Track, LoRA mit eigenen Songs. VRAM laut README: ≤ 6 GB → 2B-Turbo ohne LM, INT8 + CPU-Offload. |

**Lokal auf .2:** GPU Quadro P2200, 5 GB, Pascal (Compute 6.1). Das ist die unterste Stufe der ACE-Step-Tabelle
(nur DiT, ohne Sprachmodell-Planer). Ob es dort läuft und wie lange ein Song dauert, ist **nicht gemessen** →
Messung vor der Etappe. Der Server WKS197 mit Local Media (ComfyUI) ist ein zweiter Kandidat. ACE-Step hat einen
offiziellen ComfyUI-Weg, das passt zur vorhandenen ComfyUI-Anbindung (`llm/video_backends/_comfyui.py`).

**Nicht aufgenommen:** Suno und Udio. Für beide konnte ich keine offizielle öffentliche Entwickler-API belegen.
Zugänge über Dritte widersprechen meist den Bedingungen. Wieder prüfen, wenn es eine offizielle API gibt.
MusicGen (Meta): `facebook/musicgen-large` ist CC-BY-NC-4.0, also **nicht kommerziell**, und ohne Gesang.

**Entscheidung Till (11.10.):** Externe Anbieter **nur über OpenRouter** (ein Schlüssel, eine Abrechnung).
**Lokale Modelle** (ACE-Step) **auf jeden Fall**. Damit gilt heute:
- **Drin:** Lyria 3 Pro und Clip (OpenRouter), ACE-Step 1.5 (lokal).
- **Zurückgestellt:** ElevenLabs, Stable Audio, MiniMax und Lyria 3.5 direkt. Sie sind (Stand 11.10.) nicht über
  OpenRouter erreichbar. Sobald OpenRouter sie anbietet, erscheinen sie über den OpenRouter-Adapter automatisch
  in der Auswahl (Liste aus `/api/v1/models`, `output_modalities: audio`), ohne neuen Code. Ihre Fähigkeiten
  trägt eine kleine Tabelle im Adapter nach.

**Einbau in HydraHive:**
- Schlüssel: nur OpenRouter (wie heute). Lokale Adapter brauchen keinen Schlüssel, nur eine Adresse im Netz.
- Auswahl: Standard-Musikmodell zentral (`media_models.music`, gibt es schon), im Song änderbar. Jeder Clip
  merkt sich Anbieter, Modell und Kosten (Sidecar).
- Lokale Modelle über die vorhandene Local-Media-/ComfyUI-Schiene oder einen eigenen lokalen Adapter
  (ACE-Step-REST). Entscheidung nach der Messung.
- Lizenzhinweis je Modell in der Auswahl (aus der Adapter-Meldung). Wer veröffentlicht, sieht vorher, was gilt.

## 6. Etappen

| Etappe | Inhalt | Abnahme |
|---|---|---|
| **M1** Grundgerüst + Bibliothek | Modul, Song anlegen/listen/löschen (Papierkorb), Song-Format v1 mit Versionen und 409, Bibliothek: Quellen aus `generated/`, Atelier-Audio und Upload, Clip erzeugen über die Adapter-Schnittstelle (§5.6) mit **Lyria/OpenRouter** als erstem Adapter (Stil, Prompt, Modell, BPM und Tonart als Text), Kosten vorher anzeigen, Sidecar mit Herkunft | Song mit 3 erzeugten Clips in der Bibliothek, Neustart, alles noch da |
| **M1b** Lokale Musik-KI | Adapter **ACE-Step 1.5 lokal** (REST `acestep-api` bzw. ComfyUI, nach Messung auf .2 oder WKS197): eigener Text, Audio-Referenz, Cover, Länge bis 10 min, keine Kosten je Track; Fähigkeiten-Anzeige, Lizenzhinweis | Derselbe Song-Auftrag läuft mit Lyria (OpenRouter) und ACE-Step (lokal). Die Oberfläche zeigt je Modell nur, was es kann. |
| **M2** Arrangement + Mischpult + Mixdown | Zeitachse mit Spuren, Tempo/Takt aus Audiodateien messen (librosa), Clips verschieben/trimmen/teilen, Fades, Gain, Panorama, Mute/Solo, Abschnitte, Raster in Takten, Wellenform, Vorschau im Browser (Web Audio), Mixdown mit ffmpeg (Ansatz und Code aus `videoeditor/_audio_mix.py` übernehmen, plus Panorama), Export-Paket | Song aus 4 Clips auf 3 Spuren, Mixdown klingt wie die Vorschau, Lautheit wie eingestellt |
| **M3** Liedtext | Editor mit Abschnitt-Markern, Text beim Erzeugen an Lyria (`Lyrics:`), zurückgelieferten Text speichern, Abschnitte ↔ Text verknüpfen, Abschnitt neu erzeugen | Eigener Text mit 2 Strophen und Refrain wird gesungen, Clip kennt die Textversion |
| **M3b** Noten | MusicXML/MIDI hochladen und prüfen, Eckdaten mit `music21` auslesen, Noten anzeigen (OSMD bzw. Klavierrolle), Eckdaten in den Lyria-Prompt, Proben-Marken ↔ Abschnitte, Liedtext aus MusicXML übernehmen, Vorlage-Spur mit FluidSynth. Dazu ein **Kern-PR** für die Systempakete im Installer (§5.4) | Eine MusicXML-Datei mit Melodie, Akkorden und Text: Noten werden angezeigt, Tempo und Tonart stehen im Prompt, die Vorlage-Spur klingt notengetreu, der Text ist übernommen. Ohne FluidSynth läuft alles außer der Vorlage-Spur. |
| **M3c** Referenzen | Bilder an Lyria mitgeben; Audiodatei als Referenz beschreiben lassen (Text sichtbar, Kosten vorher); gesungenen Text mit Whisper als Liedtext-Entwurf | Foto + Prompt erzeugt passenden Clip; MP3-Referenz ergibt eine Beschreibung, die im Prompt steht und änderbar ist; Text aus einer Aufnahme landet als Entwurf im Editor |
| **M4** Agenten | Werkzeuge (§7) mit Vorschlags- und Bestätigungsweg, Skill „tonstudio-workflow“ | Buddy baut aus „mach mir einen Celtic-Trance-Song mit Intro und Refrain“ einen Song-Vorschlag, Till übernimmt ihn |
| **M5** Stems zerlegen | Clip in Gesang, Schlagzeug, Bass und Rest trennen, als neue Quellen | Vorher messen, ob die Quadro P2200 (5 GB) das schafft und wie lange es dauert. Sonst Cloud-Anbieter oder weglassen. |
| **M6** Anbindungen | Storyteller-Buch-Art `song` (Liedtext und optional Notendatei je Song) + Lese-Schnittstelle + Vorschläge zurück; Import des Export-Pakets im Media-Studio bzw. Video-Editor | Text im Storyteller ändern → Studio zeigt „neue Textversion“. Song-Paket landet als Audiospuren im Video-Editor. |

Jede Etappe ist ein eigener PR mit Tests. M1 und M2 zusammen ergeben das erste brauchbare Studio.

## 7. Agenten-Werkzeuge (M4)

| Werkzeug | Wirkung | Schutz |
|---|---|---|
| `tonstudio_songs` / `tonstudio_read` | Songs auflisten, Song mit Spuren, Abschnitten und Text lesen | nur lesen |
| `tonstudio_generate_clip` | Clip mit Lyria erzeugen (Stil, Text, BPM, Tonart) | **kostet Geld**: Kosten vorher nennen, Bestätigung im Lauf |
| `tonstudio_propose_arrangement` | Spuren, Clips und Abschnitte als **Vorschlag** setzen | Mensch übernimmt im Studio, nichts direkt |
| `tonstudio_propose_lyrics` | Liedtext als Vorschlag | wie oben |
| `tonstudio_read_score` | Eckdaten einer Notenvorlage lesen (Tonart, Tempo, Abschnitte, Akkorde) | nur lesen |
| `tonstudio_render` | Mixdown/Export-Paket starten | Hintergrund-Job, Ergebnis als Datei |

Projektgebunden und nur im Projekt des Laufs (Projekt-Sicht wie bei den Datamining-Werkzeugen).
Keine Werkzeuge für Löschen.

## 8. Sicherheit und Betrieb

- Alle Routen projektgebunden. Zugriff nur für Projektmitglieder. Freigabe `module.tonstudio`
  (Standard wie Storyteller: `admin_only`, später freigebbar).
- Pfade: nur unterhalb des Projektordners (`safe_under`). Kein Pfad aus dem Client ungeprüft an ffmpeg.
  ffmpeg mit Argumentliste, nie über die Shell.
- Upload: Größengrenze (Vorschlag 100 MB je Datei), nur Audioformate, Prüfung mit `ffprobe` vor der Annahme.
- Kosten: Jeder Erzeugungsauftrag wird mit Modell und Kosten im Sidecar und im Kostenbericht festgehalten.
  Optionale Kostengrenze je Auftrag wie im Storyteller.
- Rendern läuft als Hintergrund-Job (Job-Muster aus dem Video-Editor). Ein Neustart markiert halbe Jobs als abgebrochen.

## 9. Ausdrücklich nicht (jetzt)

- Aufnahme per Mikrofon, MIDI-Einspielen (Keyboard), virtuelle Instrumente zum Spielen, Noten schreiben oder bearbeiten (Variante b, Till 11.10.: nicht jetzt). Noten **übergeben** ist dagegen drin (§5.4).
- Notenbilder oder PDFs automatisch lesen (Notenerkennung).
- Effekte wie EQ, Hall und Kompressor je Spur sowie Automationskurven. Kandidat nach M2, eigene Spec.
- Echtzeit-Steuerung (Lyria RealTime).
- Audio direkt an Lyria (geht technisch nicht, §5.5), „Song fortsetzen“ oder Remix im Modell.
- Mehrere Nutzer gleichzeitig im selben Song. Gleichzeitiges Bearbeiten wird nur per 409 abgesichert.
- Umbau von Atelier oder Video-Editor. Sie bleiben, wie sie sind. Die Anbindung läuft über §5.

## 10. Offene Fragen (vor dem jeweiligen Schritt klären)

1. **Modelle:** siehe §5.6. OpenRouter führt heute `google/lyria-3-pro-preview` und `google/lyria-3-clip-preview`.
   Google dokumentiert inzwischen **Lyria 3.5** (Songs mit Strophen und Refrains, Länge über den Prompt
   steuerbar). Vor M1 prüfen, ob und unter welcher ID 3.5 über OpenRouter verfügbar ist und ob der
   zurückgelieferte Liedtext im Stream ankommt (heute wertet `read_audio_sse` nur Audio aus).
2. **Preise:** OpenRouter meldet für beide Lyria-Modelle heute Preis 0 (`/api/v1/models`, 11.10.).
   Das ist vermutlich unvollständig. Vor M1 die echten Kosten pro Track klären, sonst kann die
   Kostenanzeige nicht stimmen.
3. **M5 Stems:** lokal auf der GPU oder Cloud? Erst messen.
4. **Lokale Musik-KI (ACE-Step):** .2 (P2200, 5 GB) oder WKS197 (ComfyUI)? Erst messen: Laufzeit je Song, Qualität, VRAM.
5. ~~Welche Anbieter zuerst?~~ Entschieden 11.10.: nur über OpenRouter + lokal (ACE-Step).

## 11. Akzeptanz (gesamt, bis M3c)

- Song anlegen, Clips erzeugen, auf Spuren arrangieren, mischen, Mixdown als Export-Paket – ohne Shell.
- Liedtext schreiben und singen lassen. Jeder Clip kennt Modell, Prompt und Textversion.
- Notenvorlage (MusicXML/MIDI) übergeben: Eckdaten im Prompt, Vorlage-Spur notengetreu, Text aus MusicXML übernommen.
- `song.json` und das Export-Paket entsprechen §5. Eine Testdatei aus dem Video-Editor-Format lässt sich
  1:1 als Spur lesen (Test).
- Gleichzeitiges Speichern überschreibt nichts still (409). Quellen bleiben unverändert.
- Tests ohne echte Daten (Test-Safety-Regeln des Repos), ruff, Dateien höchstens ~200 Zeilen.
