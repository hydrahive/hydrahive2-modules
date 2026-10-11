# Musikstudio – Spec

Status: **ENTWURF**, wartet auf Freigabe durch Till.
Stand: 11.10.2026. Bezug: Tasks `ae837ea0` (Konzept Musikstudio) und `b7b6139a` (Media-Studio, Dach).

---

## 1. Was

Ein HydraHive-Modul **Musikstudio**, in dem man **Songs mit KI erzeugt, arrangiert, mischt und exportiert**,
gemeinsam mit den Agenten. Kernarbeit (Entscheidung Till 11.10.: Variante **a**): KI-Clips erzeugen,
auf Spuren anordnen, nach Abschnitten arrangieren, mischen, Mixdown. **Kein** Einspielen per Mikrofon
oder MIDI, **keine** virtuellen Instrumente (siehe §9).

Von Anfang an vorbereitet für zwei spätere Anbindungen (Vorgabe Till):
1. **Media-Studio** (`b7b6139a`): soll Songs und deren Spuren übernehmen können, ohne Umbau.
2. **Autorensystem für Liedtexte** (Storyteller): Liedtexte sollen dort geschrieben und ins Studio
   übernommen werden können.

## 2. Warum

Heute ist Musik auf vier Stellen verteilt, keine davon ist ein Studio:

| Ort | Kann | Fehlt |
|---|---|---|
| Atelier, Tab Audio (`music.py`, `audio_profiles.py`) | Lyria-Track erzeugen, Sound-Profile, Stil-Anker | Spuren, Arrangement, Mischen |
| Video-Editor, Audio (`SPEC-AUDIO.md`, `_audio_mix.py`) | Mehrspur mit Gain, Fades und ffmpeg-Mix | ist an ein Video gebunden, keine Song-Struktur |
| HydraVR, Tonstudio | Mischpult mit Panorama, Mute und Solo | nur in der Brille, keine Bearbeitung |
| Werkzeug `generate_music` | einzelner Track im Chat | kein Projekt, keine Versionen |

Till 29.09.: „ein wenig mehr in die professionelle Richtung“. Ein eigenes Studio bündelt das, ohne die
anderen Module zu verbiegen.

## 3. Entscheidungen

| # | Entscheidung | Begründung |
|---|---|---|
| E1 | **Eigenes Modul** `musikstudio`, nicht im Atelier | Das Atelier (1.6.6) ist schon groß. Eine Mehrspur-Oberfläche dort ließe sich später kaum ins Media-Studio herauslösen. |
| E2 | **Drei feste Übergaben** von Anfang an (§5): Song-Format, Liedtext-Verweis, Export-Paket | Das Media-Studio und der Storyteller hängen sich später an diese Übergaben, ohne dass das Studio umgebaut werden muss. |
| E3 | **Spur- und Clip-Felder gleich wie im Video-Editor** (`t_start`, `src_start`, `src_end`, `gain_db`, `fade_in`, `fade_out`, `mute`, `solo`) | Gleiche Sprache für Zeitachsen. Das Media-Studio kann eine Song-Timeline direkt als Audiospuren übernehmen. |
| E4 | **Dateibasiert im Projektordner** (`<workspace>/musikstudio/`), wie Atelier und Storyteller | Sichtbar über Samba und Git, Sicherung inklusive, kein Datenbank-Silo. |
| E5 | **Erzeugen über die HydraHive-Modelle** (OpenRouter, `hydrahive.tools._openrouter_media`), kein eigener Anbieter-Code | Ein Schlüssel, eine Kostenstelle. Neue Modelle kommen über `media_models` dazu. |
| E6 | **Nicht-destruktiv:** Quellen werden nie verändert. Schnitt, Gain und Fades stehen nur im Song. Gerendert wird erst beim Mixdown. | Jede Version bleibt wiederherstellbar, Agenten können nichts kaputt rendern. |
| E7 | **Agenten arbeiten über Vorschläge**, wie im Storyteller | Ein Agent ändert den Song nicht still. Der Mensch übernimmt oder verwirft. Kosten werden vor dem Erzeugen angezeigt. |

## 4. Begriffe und Datenmodell

```
<workspace>/musikstudio/
  songs/<song_id>/
    song.json            Song-Projekt (Format §5.1, versioniert)
    lyrics.md            Liedtext, solange kein Verweis gesetzt ist (§5.2)
    versions/<n>.json    frühere Stände von song.json (Schnappschuss je Speichern mit Änderung)
    exports/<export_id>/ Export-Paket (§5.3)
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
      "clips": [ { "id": "c1", "source_rel": "musikstudio/clips/ab12.mp3",
                   "t_start": 0.0, "src_start": 0.0, "src_end": 32.0, "gain_db": 0, "fade_in": 0.5, "fade_out": 2.0 } ] }
  ],
  "master": { "gain_db": 0, "loudness_lufs": -14 },
  "lyrics": { "ref": null }
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
  markers.json       Abschnitte mit Zeiten (für Video-Schnitt: Schnitt auf den Refrain)
```

- Das Media-Studio und der Video-Editor importieren **dieses Paket**, nicht die interne Song-Datei.
  Damit bleibt das Studio intern frei.
- Stems sind bis M5 die **gerenderten Spuren**. Ab M5 können zusätzlich aus einem fertigen Clip
  zerlegte Stems (Gesang, Schlagzeug, Bass, Rest) entstehen. Das Paketformat bleibt gleich.

## 6. Etappen

| Etappe | Inhalt | Abnahme |
|---|---|---|
| **M1** Grundgerüst + Bibliothek | Modul, Song anlegen/listen/löschen (Papierkorb), Song-Format v1 mit Versionen und 409, Bibliothek: Quellen aus `generated/`, Atelier-Audio und Upload, Clip erzeugen mit Lyria (Stil, Prompt, Modell, BPM und Tonart als Text), Kosten vorher anzeigen, Sidecar mit Herkunft | Song mit 3 erzeugten Clips in der Bibliothek, Neustart, alles noch da |
| **M2** Arrangement + Mischpult + Mixdown | Zeitachse mit Spuren, Clips verschieben/trimmen/teilen, Fades, Gain, Panorama, Mute/Solo, Abschnitte, Raster in Takten, Wellenform, Vorschau im Browser (Web Audio), Mixdown mit ffmpeg (Ansatz und Code aus `videoeditor/_audio_mix.py` übernehmen, plus Panorama), Export-Paket | Song aus 4 Clips auf 3 Spuren, Mixdown klingt wie die Vorschau, Lautheit wie eingestellt |
| **M3** Liedtext | Editor mit Abschnitt-Markern, Text beim Erzeugen an Lyria (`Lyrics:`), zurückgelieferten Text speichern, Abschnitte ↔ Text verknüpfen, Abschnitt neu erzeugen | Eigener Text mit 2 Strophen und Refrain wird gesungen, Clip kennt die Textversion |
| **M4** Agenten | Werkzeuge (§7) mit Vorschlags- und Bestätigungsweg, Skill „musikstudio-workflow“ | Buddy baut aus „mach mir einen Celtic-Trance-Song mit Intro und Refrain“ einen Song-Vorschlag, Till übernimmt ihn |
| **M5** Stems zerlegen | Clip in Gesang, Schlagzeug, Bass und Rest trennen, als neue Quellen | Vorher messen, ob die Quadro P2200 (5 GB) das schafft und wie lange es dauert. Sonst Cloud-Anbieter oder weglassen. |
| **M6** Anbindungen | Storyteller-Buch-Art `song` + Lese-Schnittstelle + Vorschläge zurück; Import des Export-Pakets im Media-Studio bzw. Video-Editor | Text im Storyteller ändern → Studio zeigt „neue Textversion“. Song-Paket landet als Audiospuren im Video-Editor. |

Jede Etappe ist ein eigener PR mit Tests. M1 und M2 zusammen ergeben das erste brauchbare Studio.

## 7. Agenten-Werkzeuge (M4)

| Werkzeug | Wirkung | Schutz |
|---|---|---|
| `musikstudio_songs` / `musikstudio_read` | Songs auflisten, Song mit Spuren, Abschnitten und Text lesen | nur lesen |
| `musikstudio_generate_clip` | Clip mit Lyria erzeugen (Stil, Text, BPM, Tonart) | **kostet Geld**: Kosten vorher nennen, Bestätigung im Lauf |
| `musikstudio_propose_arrangement` | Spuren, Clips und Abschnitte als **Vorschlag** setzen | Mensch übernimmt im Studio, nichts direkt |
| `musikstudio_propose_lyrics` | Liedtext als Vorschlag | wie oben |
| `musikstudio_render` | Mixdown/Export-Paket starten | Hintergrund-Job, Ergebnis als Datei |

Projektgebunden und nur im Projekt des Laufs (Projekt-Sicht wie bei den Datamining-Werkzeugen).
Keine Werkzeuge für Löschen.

## 8. Sicherheit und Betrieb

- Alle Routen projektgebunden. Zugriff nur für Projektmitglieder. Freigabe `module.musikstudio`
  (Standard wie Storyteller: `admin_only`, später freigebbar).
- Pfade: nur unterhalb des Projektordners (`safe_under`). Kein Pfad aus dem Client ungeprüft an ffmpeg.
  ffmpeg mit Argumentliste, nie über die Shell.
- Upload: Größengrenze (Vorschlag 100 MB je Datei), nur Audioformate, Prüfung mit `ffprobe` vor der Annahme.
- Kosten: Jeder Erzeugungsauftrag wird mit Modell und Kosten im Sidecar und im Kostenbericht festgehalten.
  Optionale Kostengrenze je Auftrag wie im Storyteller.
- Rendern läuft als Hintergrund-Job (Job-Muster aus dem Video-Editor). Ein Neustart markiert halbe Jobs als abgebrochen.

## 9. Ausdrücklich nicht (jetzt)

- Aufnahme per Mikrofon, MIDI, virtuelle Instrumente, Noten (Variante b, Till 11.10.: nicht jetzt).
- Effekte wie EQ, Hall und Kompressor je Spur sowie Automationskurven. Kandidat nach M2, eigene Spec.
- Echtzeit-Steuerung (Lyria RealTime).
- Mehrere Nutzer gleichzeitig im selben Song. Gleichzeitiges Bearbeiten wird nur per 409 abgesichert.
- Umbau von Atelier oder Video-Editor. Sie bleiben, wie sie sind. Die Anbindung läuft über §5.

## 10. Offene Fragen (vor dem jeweiligen Schritt klären)

1. **Modell:** OpenRouter führt heute `google/lyria-3-pro-preview` und `google/lyria-3-clip-preview`.
   Google dokumentiert inzwischen **Lyria 3.5** (Songs mit Strophen und Refrains, Länge über den Prompt
   steuerbar). Vor M1 prüfen, ob und unter welcher ID 3.5 über OpenRouter verfügbar ist und ob der
   zurückgelieferte Liedtext im Stream ankommt (heute wertet `read_audio_sse` nur Audio aus).
2. **Preise:** OpenRouter meldet für beide Lyria-Modelle heute Preis 0 (`/api/v1/models`, 11.10.).
   Das ist vermutlich unvollständig. Vor M1 die echten Kosten pro Track klären, sonst kann die
   Kostenanzeige nicht stimmen.
3. **Name im Menü:** „Musikstudio“ oder „Tonstudio“ (wie in HydraVR)?
4. **M5 Stems:** lokal auf der GPU oder Cloud? Erst messen.

## 11. Akzeptanz (gesamt, bis M3)

- Song anlegen, Clips erzeugen, auf Spuren arrangieren, mischen, Mixdown als Export-Paket – ohne Shell.
- Liedtext schreiben und singen lassen. Jeder Clip kennt Modell, Prompt und Textversion.
- `song.json` und das Export-Paket entsprechen §5. Eine Testdatei aus dem Video-Editor-Format lässt sich
  1:1 als Spur lesen (Test).
- Gleichzeitiges Speichern überschreibt nichts still (409). Quellen bleiben unverändert.
- Tests ohne echte Daten (Test-Safety-Regeln des Repos), ruff, Dateien höchstens ~200 Zeilen.
