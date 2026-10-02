# Spec: Musicplayer wird Mediaplayer (Audio + Video)

**Stand:** 02.10.2026 · **Modul:** `musicplayer` 1.1.2 → 1.2.0 · **Task:** 77750fb2
**Freigabe Till (02.10.2026):** „Musikplayer zum Mediaplayer, Switcher zwischen Audio und
Video“, Option A (feste Quellen), die kurzen Szenen-Clips aus dem Atelier gehören dazu,
„damit man beim Bauen nachschlagen kann, was was ist“.

## 1. Problem

1. **Generierte Musik wird nicht gefunden.** Der Import sucht nur `*.mp3` in Ordnern namens
   `generated`. Das Atelier speichert Musik unter `atelier/audio/`, Szenen-Clips unter
   `atelier/videos/` und Filme unter `atelier/films/`. Das Sprach-Werkzeug legt `.wav` ab.
   Ergebnis: Ein großer Teil der Projektmedien ist für den Player unsichtbar.
2. **Kein Video.** Szenen-Clips und fertige Filme lassen sich nirgends gesammelt ansehen.
   Beim Arbeiten am Film fehlt ein Nachschlagewerk „welcher Clip war was“.
3. Zwei Kleinigkeiten aus dem Handbuch-Befund 49ee995d:
   - Cockpit-Link `/musicplayer` (actionRegistry.ts, Core) führt ins Leere, weil das Modul keine Route hat.
   - Der Player lebt nur in der rechten Buddy-Spalte, die erst ab `xl` sichtbar ist.

## 2. Ziel

Ein Mediaplayer pro Projekt mit Umschalter **Audio | Video**:
- Bibliothek, Abspielen, Hochladen und Import für beide Medienarten.
- Import „Aus dem Projekt“ findet alle bekannten Ablageorte, gruppiert nach Herkunft,
  mit sprechenden Titeln (Prompt bzw. Datum aus den Atelier-Sidecars).
- Szenen-Clips und Filme aus dem Atelier sind nachschlagbar (Prompt, Modell, Dauer).

## 3. Nicht-Ziele

- Kein Schnitt, kein Umwandeln (MOV/MKV → MP4). Das gehört ins Media-Studio (b7b6139a).
- Keine automatische Anmeldung neuer Medien durch Atelier/Agent-Werkzeuge (Option C, später).
- Kein Durchsuchen des ganzen Projekts (Option B, verworfen: findet Backups, Testaufnahmen,
  Altplatten-Archive).
- Interne Modul-ID bleibt `musicplayer` (Bestandsdaten, Tabellen, Hub-Eintrag, Hilfe-Seite).

## 4. Medienarten und Formate

| Art   | Endungen                          | MIME beim Abspielen              |
|-------|-----------------------------------|----------------------------------|
| audio | .mp3 .wav .ogg .m4a .flac         | audio/mpeg, audio/wav, audio/ogg, audio/mp4, audio/flac |
| video | .mp4 .webm                        | video/mp4, video/webm            |

Die Art wird aus der **Endung** bestimmt (eine Tabelle, eine Stelle), nicht aus dem
Content-Type des Uploads. Andere Endungen werden abgelehnt (400).

## 5. Quellen für den Import (Option A)

Feste Liste, relativ zum Projekt-Workspace, eine Stelle im Code (`sources.py`):

| Quelle (Gruppe in der UI)  | Pfad                 | Art        | Titel aus                          |
|----------------------------|----------------------|------------|------------------------------------|
| Agent (generiert)          | `generated/`         | audio+video| Dateiname                          |
| Atelier · Musik            | `atelier/audio/`     | audio      | Sidecar `<name>.json`: prompt      |
| Atelier · Szenen-Clips     | `atelier/videos/`    | video      | Sidecar `<id>.json`: prompt, model, duration |
| Atelier · Filme            | `atelier/films/`     | video      | Sidecar: created_at („Film vom …“) |
| Hochgeladen (Medienordner) | `media/audio/`, `media/video/` | jeweilige Art | Dateiname            |

Regeln:
- **Nur direkte Dateien** im Quellordner, keine Unterordner (atelier/audio/profiles u. ä. bleiben draußen).
  Ausnahme `generated/`: eine Ebene tiefer erlaubt (Agent-Workspaces legen dort Unterordner an).
- Symlinks werden übersprungen, alle Pfade bleiben im Workspace (wie heute `_safe_generated_file`).
- Sidecar fehlt oder ist kaputt → Titel = Dateiname, kein Fehler.
- Dateien, die selbst in der Bibliothek liegen (`media/audio`, `media/video` mit UUID-Namen aus
  Upload/Import), werden nicht als Importquelle angeboten. Erkennung: Dateiname steht in der
  Tracks-Tabelle (`filename`).
- Maximal 500 Einträge pro Abruf (neueste zuerst), damit große Projekte die Seite nicht lahmlegen.

## 6. Datenmodell

Migration `004_media_kind.sql` (additiv, wie die bestehenden):
- `ALTER TABLE module_musicplayer_tracks ADD COLUMN media_kind TEXT NOT NULL DEFAULT 'audio'`
  → alle Bestandstracks bleiben Audio.
- `ADD COLUMN ext TEXT NOT NULL DEFAULT 'mp3'` → Endung der gespeicherten Datei.
- `ADD COLUMN meta TEXT NOT NULL DEFAULT ''` → JSON mit prompt/model/duration aus dem Sidecar
  (nur zur Anzeige, max. 2 KB).

Speicherort der Bibliotheksdateien:
- audio: `<projekt>/media/audio/<uuid>.<ext>` (wie heute, nur mit Endung statt fest `.mp3`)
- video: `<projekt>/media/video/<uuid>.<ext>` (neu, gleiche Symlink-Schutzregeln)

**Import = Verweis oder Kopie?** Kopie wie heute (Bibliothek bleibt stabil, auch wenn das
Atelier aufräumt). Für Videos ist das bei den vorhandenen Größen vertretbar (alle Szenen-Clips
aller Projekte zusammen ca. 65 MB). Dedup über `source` (wie heute).

## 7. API (unter `/api/modules/musicplayer`)

Bestehende Endpunkte bleiben und bekommen einen optionalen Filter:
- `GET  /projects/{pid}/tracks?kind=audio|video` (ohne kind: alle). `TrackOut` erhält `media_kind`, `ext`, `meta`.
- `POST /projects/{pid}/tracks` Upload: Art aus der Endung, Limit Audio 50 MB, **Video 60 MB**
  (nginx-Grenze für `/api/` liegt bei 64 MB; größere Uploads brauchen eine Core-Änderung, nicht Teil dieser Spec).
- `GET  /projects/{pid}/tracks/{id}/stream` → richtiger MIME-Typ, Download-Name mit richtiger Endung.
  Range-Anfragen (Spulen im Video) liefert Starlette `FileResponse` bereits (geprüft: 1.6.0).
- `DELETE …` unverändert.

Import:
- `GET  /projects/{pid}/sources?kind=audio|video` → Liste `{source, group, path, kind, title, meta, size_bytes, mtime, already_imported}`.
- `POST /projects/{pid}/sources/import` `{path}` → wie heute, für alle Quellen.
- Alte Endpunkte `/generated` und `/generated/import` bleiben als Alias (Buddy-Box älterer Bundles).

Rechte unverändert (`require_project_access` read/write/admin, Stream-Token per Query).

## 8. Oberfläche

**Buddy-Kachel (rechte Spalte, wie heute):**
- Titel „Medien“, darunter Umschalter **Audio | Video** (Auswahl wird pro Projekt im Browser gemerkt).
- Audio: heutiger Player (Playlist, Shuffle, Repeat, Equalizer).
- Video: kleiner Player (16:9) über der Liste, Klick auf Eintrag spielt ab; Knopf „Vollbild“
  (Browser-Vollbild des `<video>`) und „Groß öffnen“ → eigene Seite.
- Liste zeigt bei Atelier-Einträgen den Prompt als Untertitel (gekürzt, voller Text im Tooltip),
  dazu Modell und Dauer, wenn bekannt → das „Nachschlagen“.
- Import-Bereich „Aus dem Projekt“ ersetzt „Generierte Musik“, gruppiert nach Herkunft (Abschnitt 5),
  zeigt nur die gerade gewählte Art.
- Upload-Knopf nimmt die erlaubten Endungen der gewählten Art.

**Musik läuft beim Umschalten weiter (Till, 02.10.2026):**
- Wechsel Audio → Video stoppt die Musik nicht. Der Audio-Player lebt in der Projektansicht,
  nicht in der Audio-Ansicht; das `<audio>`-Element bleibt beim Umschalten erhalten.
- In der Video-Ansicht zeigt eine schmale Leiste das laufende Lied mit Pause/Weiter;
  Klick auf den Titel wechselt zurück zu Audio.
- Es spielt immer nur eins mit Ton: Startet ein Video, pausiert die Musik. Startet die Musik
  (Leiste), pausiert das Video.
- **Musik setzt nach dem Video fort (Till, 02.10.2026, Variante B):** Hält das Video an oder
  endet es, läuft die Musik an derselben Stelle weiter — nur wenn sie vor dem Video lief.
  - Fortsetzen erst nach kurzer Wartezeit (300 ms) und nur, wenn das Video dann noch steht und
    keine Maustaste/Finger auf dem Video ist. Grund: Chrome pausiert beim Spulen über die
    Zeitleiste kurz, und beim Wechsel zum nächsten Video entsteht ebenfalls eine kurze Pause —
    dabei darf die Musik nicht kurz anspringen.
  - Startet oder stoppt der Nutzer die Musik selbst (Leiste), wird nichts mehr fortgesetzt.
  - Wechsel zu Audio, während das Video läuft oder kurz davor stand: Musik setzt fort.
  - Hinweis C (leiser statt aus) ist bewusst nicht Teil; siehe Task 9723c628.
- Das laufende Lied wird über seine ID gemerkt, nicht über die Position in der Liste:
  Import/Upload/Löschen während der Wiedergabe wechselt nicht das Lied. Wird das laufende
  Lied gelöscht, stoppt die Wiedergabe.
- Die Bibliothek wird einmal für beide Arten geladen und im Browser getrennt, damit die
  Audio-Liste beim Blick auf Video stehen bleibt.
- Grenze: Wer die Seite verlässt (anderer Menüpunkt, anderes Projekt), beendet die Musik
  weiterhin. Seitenübergreifende Wiedergabe ist nicht Teil dieser Etappe.

**Eigene Seite `/musicplayer` (neu, behebt den toten Cockpit-Link):**
- Volle Breite, gleiche Komponenten, Video groß. Projekt = aktives Projekt (wie Buddy); ohne Projekt
  Hinweis „Projekt wählen“.
- Damit ist der Player auch auf kleinen Bildschirmen erreichbar (die Buddy-Spalte bleibt `xl`).
- Nav-Eintrag „Mediaplayer“ (Gruppe working).

Texte über i18n (de + en), Modulname im Manifest „Mediaplayer“.

## 9. Sicherheit

- Pfade nur aus der festen Quellenliste, keine Nutzerpfade außerhalb davon (Import prüft `path`
  gegen die Liste + Workspace-Grenze + Symlink-Verbot, wie heute).
- Art aus Endung, Upload-Größen begrenzt, gespeichert unter UUID-Namen.
- Sidecar-Inhalte werden nur angezeigt (Text), nie ausgeführt; Länge begrenzt.
- Stream-Token wie heute (kurzlebig, Query), keine neuen Wege.

## 10. Tests (TDD)

Backend (pytest, vorhandene Isolation):
- Quellen: findet atelier/audio, atelier/videos (+Sidecar-Prompt), atelier/films, generated (mp3+wav+mp4),
  media/*; ignoriert Unterordner (profiles), Symlinks, fremde Endungen, Bibliotheksdateien selbst.
- Sidecar kaputt/fehlt → Dateiname als Titel.
- Import Video → `media/video/<uuid>.mp4`, media_kind=video, meta mit prompt; Doppelimport → 409.
- Stream: MIME je Endung, Range-Anfrage → 206.
- Upload: .webm ok, .mov → 400, Video > 60 MB → 413.
- Migration: Bestandstrack bleibt audio/mp3 und spielt weiter.
- Alias /generated liefert weiterhin Ergebnisse.

Frontend (vitest, ohne App-Importe):
- Umschalter filtert Liste und Import nach Art; Titel/Untertitel aus meta.
- Playlist-Logik nach ID (`playlist.ts`): weiter/zurück/Ende/Shuffle/Repeat; neues Lied vorne in
  der Liste ändert weder das laufende noch das nächste Lied; gelöschtes Lied → kein aktuelles.
- Struktur (pytest, Quelltext): `<audio>` und `useAudioPlayer` in der Projektansicht, nicht in der
  Audio-Ansicht; Video meldet `onPlay`; Bibliothek ohne Art-Filter geladen.
- Fortsetzen nach Video (`mediaFocus.ts`, vitest): merkt nur, wenn Musik lief; bleibt gemerkt bei
  Video-Wechsel; kein Fortsetzen bei laufendem Video oder gedrückter Maus; Vertragstest für
  Verdrahtung (onPause/onEnded/Pointer/Aushängen, Leiste löscht das Gemerkte).

Prüfung auf dem Test-Server im Browser: Projekt mit echten Atelier-Clips, Audio und Video
importieren, abspielen, spulen, Vollbild, Seite `/musicplayer`, Bestandstracks spielen weiter.

## 11. Umfang / Reihenfolge

Ein PR im Modul-Repo (musicplayer 1.2.0), Commits getrennt nach Backend-Quellen, Backend-Video,
Frontend, Doku/Hilfe. Core-Änderung nur, falls der tote Link nach dem Nav-Eintrag nicht von selbst
greift (actionRegistry nennt `/musicplayer` bereits).
