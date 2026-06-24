# Musicplayer — MP3-Player in der Buddy-Box

## Was
Ein kompaktes Modul, das selbstgemachte (oder hochgeladene) MP3s in einer
hübschen Buddy-Box abspielt. Player mit Play/Pause, Prev/Next, Seek-Bar,
Lautstärke, Track-Liste und einer kleinen Equalizer-Animation. Der Upload-Knopf
ist **nur für Admins** sichtbar; das Abspielen steht allen eingeloggten Usern offen.

## Warum
Till generiert Musik (generate_music) und will sie an einem Ort sammeln und direkt
neben Buddy hören — ohne Umweg über Datei-Downloads. Bewusst schlank: nur die
Buddy-Box, kein eigener Tab. Upload + Verwaltung passieren in derselben Box.

## Wie (grob)

### Storage
- Dateien: `settings.data_dir / "modules" / "musicplayer" / <uploader>/ <id>.mp3`
  (uploader = Admin-Username; ein gemeinsamer Pool, da Admin für alle hochlädt).
- Metadaten: Tabelle `module_musicplayer_tracks`
  (id, title, filename, size_bytes, uploaded_by, created_at).
- Single Source für die Liste ist die DB; die Datei ist das Audio-Backing.
  Upload und Delete halten beide konsistent (DB-Zeile + Datei atomar).

### Backend-Routen (Prefix `/api/modules/musicplayer`)
| Methode | Pfad | Auth | Zweck |
|---|---|---|---|
| GET | `/tracks` | require_auth | Track-Liste (id, title, size, uploaded_by, created_at) |
| GET | `/tracks/{id}/stream` | require_auth | Audio ausliefern (FileResponse, Range-fähig fürs Seeking) |
| POST | `/tracks` | **require_admin** | Multipart-Upload (mp3), Titel optional (Default = Dateiname) |
| DELETE | `/tracks/{id}` | **require_admin** | Track + Datei löschen |

- Upload-Validierung: Endung `.mp3` + Content-Type `audio/*`, Größenlimit
  (z.B. 30 MB), Dateiname säubern (keine Pfad-Traversal), eigene UUID als Speichername.
- Stream nutzt `FileResponse` (FastAPI/Starlette beantwortet Range-Requests selbst →
  der `<audio>`-Tag kann seeken).

### Frontend — Buddy-Box (`MusicPlayerBuddyBox`)
- `CollapsibleBox` (wie BoardGamesBuddyBox), Icon `Music`, eigene Akzentfarbe.
- Ein einziges `<audio ref>`-Element (kein externes Lib). State: Track-Liste,
  aktiver Index, playing, currentTime/duration, volume.
- Controls: ⏮ Prev · ⏯ Play/Pause · ⏭ Next, Seek-Bar (`<input range>` an
  currentTime), Volume-Slider, Zeit `m:ss / m:ss`.
- Track-Liste darunter: Klick wählt + spielt; aktiver Track hervorgehoben.
- "Schnickschnack": CSS-Equalizer-Balken (animieren nur wenn `playing`), sanfter
  Hover/Active-Glow im Akzent.
- Audio-`src` = `/api/modules/musicplayer/tracks/{id}/stream?token=<jwt>` — der
  `<audio>`-Tag kann keinen Authorization-Header setzen, daher Auth via Query-Token
  (exakt das Pattern aus core `files.py`: `get_current_user_optional` + `?token=`,
  JWT mit `_decode` prüfen). FileResponse beantwortet Range-Requests selbst.
- **Admin-only**: `useAuthStore().role === "admin"` blendet einen Upload-Button +
  versteckten `<input type=file accept="audio/mpeg">` ein; nach Upload Liste neu laden.
  Delete-Icon je Track ebenfalls nur für Admin.

### i18n
- de/en Keys in `index.tsx` (mp_title, mp_upload, mp_uploading, mp_empty,
  mp_delete, mp_play, mp_pause, mp_next, mp_prev, mp_upload_error, mp_too_large).

## Akzeptanzkriterien
- [ ] Buddy-Box zeigt Track-Liste, Player spielt MP3s ab, Seek/Volume funktionieren.
- [ ] Admin sieht Upload-Button + Delete; Nicht-Admin sieht nur den Player.
- [ ] Upload speichert Datei + DB-Zeile; Delete entfernt beides.
- [ ] Stream ist Range-fähig (Seeking im Player springt).
- [ ] Upload lehnt Nicht-Audio/zu große Dateien mit klarer Fehlermeldung ab.
- [ ] Pfad-Traversal im Dateinamen unmöglich (UUID-Speichername).
- [ ] Backend-Tests grün (list/upload/admin-guard/delete/validation, auth gemockt).
- [ ] Alle Dateien ≤200 Z. `tsc -b` + `vite build` grün.

## Nicht in diesem Scope
- Kein eigener Vollbild-/Mediathek-Tab (nur Buddy-Box).
- Keine Playlisten/Shuffle/Repeat (Kandidat für Runde 2).
- Kein Transcoding/Cover-Extraktion (ID3) — Titel kommt aus Upload-Feld/Dateiname.
- Kein Auto-Import generierter Musik (Kandidat für Runde 2).
