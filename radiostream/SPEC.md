# Radiostream – eigenes Webradio-Sendestudio

> Neues Modul `radiostream` (Name von Till, 26.10.). Idee von Till (26.10.2026): Früher hatte er ein eigenes Webradio-Sendestudio. Die Musik liegt auf
> dem NAS. Gehört wird zuhause und über Tailscale. Dazu kommt Live-Senden für einen Bekannten mit Lizenz
> (My-Hitradio24 über laut.fm). Task 3506120a.
> **Status: Plan. Gebaut wird erst nach Tills Freigabe, Etappe für Etappe.**

## Problem

Till hat eine große Musiksammlung, aber kein Programm, das sie als Radio sendet. Der Mediaplayer (`musicplayer`) spielt
nur einzelne Dateien im eigenen Browser ab. Er sendet nicht, kennt keine Rotation und keine Überblendung und kann nicht
live gehen.

## Ziel

Ein Sendestudio in HydraHive:
- **Rund um die Uhr** läuft ein Programm aus der eigenen Sammlung. Es wiederholt nicht ständig dieselben Titel und
  blendet weich über.
- **Zuhören** geht im Heimnetz und über Tailscale, mit jedem Player (Browser, VLC, Handy, Smart-Speaker).
- **Live gehen** ist mit einem Knopf möglich, mit Mikrofon im Browser, Jingles und automatischem Absenken der Musik.
- **„Auf Sendung“** schickt das Programm an einen externen Sender (Icecast/Shoutcast, z. B. My-Hitradio24 über laut.fm).
- **Bedienung** läuft komplett über die Oberfläche, ohne Terminal.

## Befund (26.10.2026, nur gelesen)

**Musik:** `smb://molkewolke.local/Plex_Musik/` (NAS 192.168.178.3). Der Zugang liegt im Safe als Credential
`plexmusik` (Typ basic, `url_pattern` = diese Adresse).
- 2.515 Künstlerordner, 22.591 Ordner, 175.465 Dateien.
- Darunter 117.922 MP3 und 57.444 FLAC, außerdem 67 M4A, 16 WMA, 13 WAV.
- Aufbau im Plex-Stil: Künstler/Album/Titel.
- **Plex nutzt dieselbe Freigabe.** Deshalb gilt **nur lesen** (keine Tags, Cover oder Ordner ändern).

**Messung:**
- Das Auflisten aller Ordner über SMB dauert 59 s.
- Kopfdaten lesen (mutagen über smbprotocol, 300 zufällige Titel): 15 Titel/s bei einem Strang, alle 300 lesbar.
  Rund 175.400 Titel brauchen also etwa 3,2 h bei einem Strang.
- Vorhandene Angaben: Künstler, Titel und Album bei 100 %, Genre bei 98 %, Jahr bei 99 %, Länge bei 100 %.

**Im Kern vorhanden:**
- `smbprotocol` (Abhängigkeit des Kerns) für SMB-Zugriff ohne Einbinden und ohne root.
- Credential-Store, SQLite mit FTS5 (3.46), `register_job`.
- `ffmpeg` und `ffprobe`.
- Modul-Dienste über `has_service` mit `extension/install.sh` / `uninstall.sh`.

**Nicht vorhanden:** `mutagen` (MIT-Lizenz, reines Python, ~300 KB), Icecast2, Liquidsoap.

## Aufbau (Weg A, von Till gewählt)

```
                                                       Hörer (Browser, VLC, Handy) – ohne Anmeldung
                                                                     │  http://<server>:8800/
                                                         nginx-Server „Hörer-Seite“ (eigener Port)
                                                          ├─ /          statische Seite mit Player
                                                          ├─ /stream    → Icecast (127.0.0.1)
                                                          └─ /jetzt     → Icecast-Status (nur Titel)
NAS (nur lesen) ──SMB──▶  Modul radiostream (HydraHive-Backend)
                           ├─ Bibliothek: Einlesen, Suche, Rotation (SQLite + FTS5)
                           ├─ Steuerung: Playlist-Wahl, Sendeplan, Live-Knopf
                           └─ HTTP-Schnittstelle nur für Liquidsoap („nächster Titel“, Datei holen)
                                       │
                           Liquidsoap (Dienst): spielt ab, Überblendung, Lautheit, Jingles, Live-Übernahme
                              ├──▶ Icecast (Dienst, lokal): /radio.mp3 für zuhause und Tailnet
                              └──▶ externe Ziele (Icecast/Shoutcast), nur bei „Auf Sendung“
```

- **Icecast** und **Liquidsoap** sind die bewährten Bausteine von Webradios. Beide sind frei (GPL) und laufen als
  eigene Prozesse, als `has_service` des Moduls (Etappe 2).
- Das **Modul entscheidet, was läuft**. Liquidsoap fragt das Modul nur nach dem nächsten Titel. So bleiben Rotation,
  Sendeplan und Wünsche Python-Code mit Tests. Die Liquidsoap-Konfiguration bleibt klein.
- **Hören ohne HydraHive (Till, 26.10.):** Hörer brauchen kein HydraHive-Konto und keine Anmeldung. Sie sehen nichts
  von HydraHive und kommen nie an ein Modell (LLM) heran. Dafür gibt es eine **eigene Radio-Seite auf einem eigenen
  Port**, siehe „Hörer-Seite“.
- Icecast lauscht nur auf 127.0.0.1. Nach außen spricht ausschließlich die Hörer-Seite.

## Hörer-Seite (Till, 26.10.: „auch Hörer ohne HydraHive, nur ein Streamplayer, extra Port, kein LLM-Kontakt“)

**Grundsatz: völlig getrennt von HydraHive.** Die Hörer-Seite ist ein **eigener nginx-Server-Block** auf einem eigenen
Port (**8800**, einstellbar; Till 26.10.). Er kennt nur drei Wege und sonst nichts:

| Weg | Ziel | Inhalt |
|---|---|---|
| `/` | statische Dateien unter `/var/lib/hydrahive2/radiostream/public/` | eine HTML-Seite mit Player |
| `/stream` (und `/stream.mp3`, `/stream.m3u`) | `127.0.0.1:<icecast>/radio.mp3` | der Audio-Stream |
| `/jetzt` | `127.0.0.1:<icecast>/status-json.xsl` | „Jetzt läuft“ (nur Künstler/Titel, per nginx gefiltert) |

**Bewusst nicht vorhanden:**
- keine Weiterleitung an das HydraHive-Backend (`127.0.0.1:8001`) und kein `/api`;
- keine Anmeldung und keine Cookies;
- keine Module, kein Chat und kein Agent. Ein Modell ist auf keinem Weg erreichbar.
Alles andere liefert 404.
- **Admin-Teil von Icecast** (`/admin`) ist über die Hörer-Seite nicht erreichbar. Nur über 127.0.0.1.
- **Die Seite selbst:**
  - Reines HTML, CSS und kleines JavaScript, ohne Fremd-Dateien von außen (keine CDNs, keine Schriften, kein Tracking).
  - Inhalt: Sendername, Logo, Play/Pause, Lautstärke, „Jetzt läuft“ (fragt `/jetzt` alle 15 s), die letzten Titel und
    Links zum Öffnen in VLC/iTunes (`.m3u`/`.pls`).
  - Funktioniert auf dem Handy.
  - `Content-Security-Policy: default-src 'self'` und weitere Sicherheits-Kopfzeilen wie bei der Haupt-Oberfläche.
- **Gestaltung im Studio:** Sendername, Untertitel, Logo und Farben trägt man im Modul ein (Reiter „Hörer-Seite“). Das
  Modul **erzeugt daraus statische Dateien**. Die Hörer-Seite ruft also nie HydraHive auf, um sich anzuzeigen.
- **Erreichbarkeit:** Wo Hörer herkommen dürfen, ist einstellbar:
  - **„Heimnetz und Tailscale“:** nginx erlaubt nur private Adressen (`10/8`, `172.16/12`, `192.168/16`),
    Tailscale (`100.64/10`) und `127.0.0.1`. Alles andere bekommt 403.
  - **„Alle“** (Standard, Till 26.10.): für Hörer aus dem Internet. Den Port leitet Till selbst durch Firewall und
    Fritzbox. Das Modul öffnet am Router nichts. Der Hinweis dazu steht in der Oberfläche.
  - **„Aus“:** Die Hörer-Seite ist nicht erreichbar, nur der interne Stream läuft.
- **Schutz vor Überlast:**
  - Höchstzahl gleichzeitiger Hörer (Icecast `max-listeners`, Standard 50, einstellbar).
  - nginx begrenzt Verbindungen je Adresse.
- **Hörerzahl** erscheint im Studio (aus dem Icecast-Status), ohne Adressen zu speichern.
- **Externe Ziele (laut.fm)** sind davon unabhängig. Dort hören die Hörer über laut.fm, nicht über diesen Port.

**Wann:** Die Hörer-Seite kommt mit **Etappe 2** (Sendebetrieb), weil es vorher keinen Stream gibt. Etappe 1 bleibt
die Bibliothek.

## Etappen

Je Etappe gilt dieselbe Reihenfolge: Bauplan-Nachtrag, rote Tests, Code, Prüfung, PR, Tills OK.

1. **Bibliothek** (dieser Bauplan): einlesen, durchsuchen, anhören im Browser.
2. **Sendebetrieb und Hörer-Seite:** Icecast und Liquidsoap als Dienst, AutoDJ mit Rotation und Überblendung, eigene
   Hörer-Seite auf eigenem Port (ohne HydraHive, ohne Anmeldung).
3. **Live-Studio:** Mikrofon im Browser, Jingles, Musik absenken („Ducking“), „Jetzt läuft“, Wünsche.
4. **Auf Sendung:** externe Ziele mit Zugangsdaten aus dem Safe, Senden ein und aus, Zustand sichtbar.
5. **Sendeplan:** Zeitfenster mit Regeln (z. B. „morgens Pop, abends Rock“) und Sendungen.
6. **Optional:** KI-Moderator, der Titel ansagt (lokal mit Piper, kostenlos).

## Bauplan Etappe 1 – Bibliothek (26.10.)

### Einstellungen (Oberfläche → Radiostream → Einstellungen, nur Admins)

- **Musikquelle:**
  - Adresse `smb://host/freigabe[/unterordner]`.
  - Zugang: Auswahl aus den eigenen Safe-Einträgen vom Typ basic. Vorbelegt ist der Eintrag, dessen `url_pattern` zur
    Adresse passt.
  - Knopf „Verbindung prüfen“ zeigt die Anzahl der Ordner der obersten Ebene oder einen verständlichen Fehler.
- Etappe 1 kennt **eine Quelle**. Die Datenstruktur erlaubt aber mehrere Quellen (`source_id`).
- Gespeichert wird in der Modul-DB. Das Passwort steht **nie** in der Modul-DB, nur der Name des Safe-Eintrags.

### Einlesen

- **Ablauf:**
  1. Ordner per SMB durchgehen (smbprotocol, wie in der Messung).
  2. Für jede Audiodatei (`mp3`, `flac`, `m4a`, `ogg`, `opus`, `wav`, `wma`) Größe und Änderungszeit vergleichen.
  3. Nur Neues oder Geändertes öffnen und die Kopfdaten mit mutagen lesen: Künstler, Albumkünstler, Titel, Album,
     Genre, Jahr, Titelnummer, Länge, Bitrate, Abtastrate, Format, ReplayGain falls vorhanden.
  4. Fehlt ein Tag, kommt er aus dem Pfad: `Künstler/Album/NN Titel.ext`.
- **Gelöschte Dateien** (beim vollständigen Durchgang nicht mehr gesehen) werden als `missing` markiert, nicht gelöscht.
  Kommen sie wieder, sind sie wieder da. Später geht so keine Abspiel-Historie verloren.
- **Hintergrund:**
  - Läuft in einem Hintergrund-Thread, nie in der Ereignisschleife.
  - **Ein Strang** (Till 26.10.: „gemütlich reicht“). Erstes Einlesen etwa 3 h, NAS und Plex bleiben entspannt.
    Die Zahl ist eine Konstante; mehr Stränge nur nach Rücksprache.
  - Speichern in Paketen zu 500 Titeln. Ein Neustart setzt am letzten Paket fort und fängt nicht von vorn an.
- **Fortschritt** sichtbar: Ordner durchgesehen, Titel neu/geändert/fehlend, Fehler, geschätzte Restzeit, Abbrechen.
- **Automatisch:** `register_job` prüft stündlich, ob ein Durchgang fällig ist (Standard: täglich um 4 Uhr). Beim
  ersten Mal startet der Durchgang über den Knopf „Bibliothek einlesen“.
- **Dateien, die nicht lesbar sind** (kaputt, unbekanntes Format), landen in einer Fehlerliste mit Pfad und Grund. Sie
  brechen nichts ab.

### Daten (Modul-DB, Migration `001_library.sql`)

- `module_radiostream_sources`: `source_id`, `url` (ohne Passwort), `credential_name`, `owner`, `last_scan_*`, `state`.
- `module_radiostream_tracks`:
  - `track_id` (stabil: Hash aus `source_id` und Pfad), `source_id`, `rel_path` (einmalig je Quelle), `size`, `mtime`.
  - `artist`, `album_artist`, `title`, `album`, `genre`, `year`, `track_no`, `duration_s`, `bitrate`, `sample_rate`,
    `format`, `replaygain_db`.
  - `state` (`ok`, `missing`, `error`), `error_code`, `first_seen`, `last_seen`.
- `module_radiostream_tracks_fts`: FTS5 über Künstler, Titel, Album und Genre (Inhalt aus `tracks`, per Trigger aktuell).
- `module_radiostream_scan_errors`: Pfad, Code, Zeitpunkt (höchstens die letzten 5.000).
- Indizes auf `(source_id, rel_path)`, `artist`, `genre`, `year`, `state`.

### Abspielen im Browser (nur zum Vorhören)

- `GET /api/modules/radiostream/tracks/{id}/audio` liest die Datei per SMB und reicht sie mit `Range` durch.
- **FLAC/WMA** werden für das Vorhören mit ffmpeg nach MP3 192k umgewandelt, ohne Zwischendatei.
- Nur angemeldete Nutzer mit der Freigabe `module.radiostream`.

### Schnittstellen

Alle Schnittstellen verlangen eine Anmeldung. Einstellungen und Einlesen sind nur für Admins.

- `GET/PUT /settings` und `POST /settings/test`.
- `POST /scan` (starten), `GET /scan` (Stand), `POST /scan/cancel`.
- `GET /tracks?q=&artist=&genre=&year_from=&year_to=&state=&limit=&cursor=`:
  - Volltextsuche über FTS5.
  - Blättern mit Cursor, höchstens 200 Titel je Seite.
- `GET /stats`: Anzahl der Titel, Gesamtdauer, Formate, die Top-Genres und Jahrzehnte, Fehlerzahl.
- `GET /artists` und `GET /genres`: Listen mit Anzahl.
- **Fehler** über `coded()` mit eigenem Text in Deutsch und Englisch. Codes sind zum Beispiel `radiostream_source_unreachable`,
  `radiostream_auth_failed`, `radiostream_share_not_found`, `radiostream_scan_running`,
  `radiostream_not_configured`.

### Oberfläche (Modul-Seite „Radiostream“)

- **Reiter „Bibliothek“** (Etappe 1 sichtbar, die übrigen Reiter erscheinen erst mit ihren Etappen):
  - Oben Zahlen: Titel, Spielzeit, Künstler, Genres. Daneben der Stand des Einlesens mit Fortschrittsbalken.
  - Suchfeld. Filter für Genre, Jahrzehnt und Format (MP3/FLAC).
  - Liste: Künstler, Titel, Album, Jahr, Länge, Format. Mit ▶ zum Vorhören.
  - Lange Listen werden virtuell gerendert, damit 175.000 Titel flüssig bleiben.
- **Leerer Zustand:** ein Hinweis „Noch keine Musik – Quelle in den Einstellungen eintragen“ mit Knopf.
- Handy (393/375 px) kommt ohne Querscrollen aus: Die Liste zeigt dort zweizeilig Künstler – Titel und Album · Jahr.
- Texte auf Deutsch und Englisch, ohne Hinweise auf Terminal, Dateien oder Pfade außer der Quell-Adresse.

### Manifest

- `id: radiostream`, Name „Radiostream“, Symbol `Radio`, `nav_group: working`.
- Freigabe `module.radiostream` (Standard `admin_only`).
- `has_service: false`. Die Dienste kommen erst in Etappe 2.
- **Abhängigkeit mutagen:** Module bringen bisher keine Python-Pakete mit. Zwei Wege:
  - **(a)** mutagen kommt in die Kern-Abhängigkeiten (`core/pyproject.toml`). Das ist ein kleiner Kern-PR vorab.
  - **(b)** Das Modul bringt eine Kopie mit Herkunftsangabe mit (MIT).
  - **Empfehlung (a):** Das ist sauber, wird mit jedem Update gepflegt und ist auch für Mediaplayer und Studio nützlich.

### Prüfung Etappe 1

- **Tests:**
  - Einlesen mit SMB-Attrappe: Ordnerbaum im Speicher, echte kleine MP3/FLAC-Dateien als Bytes.
    - Neu, geändert, unverändert, verschwunden, wieder da, kaputte Datei.
    - Tags fehlen, dann Ableitung aus dem Pfad.
    - Fortsetzen nach Abbruch.
    - Höchstzahl der Stränge.
  - Suche (FTS5), Filter, Cursor, Statistiken.
  - Rechte (Gast, Nutzer ohne Freigabe, Admin).
  - Das Passwort taucht nie in DB, Log oder Antwort auf.
- Mutanten, bis keiner überlebt. Gegenprobe gegen `main`.
- **Echte Probe:** Auf hydratest wird die echte Freigabe eingelesen (nur lesen) und Zeit und Anzahl gemessen. Danach
  folgen Suche und Vorhören von MP3 und FLAC.
- E2E bei 1600, 1280, 393 und 375 px.

### Nicht in Etappe 1

Stream, Icecast, Liquidsoap, Playlists, Rotation, Live, externe Ziele, Sendeplan, Cover-Bilder, Bewertungen, Schreiben
auf das NAS.

## Spätere Etappen (Grobskizze, je Etappe eigener Bauplan)

**Etappe 2 – Sendebetrieb:**
- `extension/install.sh` installiert `icecast2` und `liquidsoap` (apt). Dienste `hydrahive-radiostream-icecast` und
  `hydrahive-radiostream-liquidsoap`, nur auf 127.0.0.1. Passwörter werden erzeugt und liegen in `/etc/hydrahive2`, 0600.
- **AutoDJ:**
  - Gleicher Künstler frühestens nach 60 min, gleicher Titel frühestens nach 3 Tagen (einstellbar).
  - Weiche Überblendung, gleiche Lautheit (ReplayGain oder Liquidsoap-Normalisierung).
  - Stille am Titelende wird abgeschnitten.
- **Stream** über die Hörer-Seite (MP3 192k, optional AAC). Der nginx-Server-Block wird vom Modul geschrieben
  (`/etc/nginx/sites-available/hydrahive-radiostream`). Vor dem Neuladen läuft `nginx -t`, die alte Fassung bleibt bei
  Fehlern.
- **Tests für die Abschottung:**
  - Die erzeugte nginx-Konfiguration enthält nur `/`, `/stream*` und `/jetzt`.
  - Sie enthält keinen Weg zum HydraHive-Port.
  - Die Adressregeln passen zur gewählten Erreichbarkeit.
  - Auf hydratest: `/api/health` über den Radio-Port antwortet mit 404.
- **Offen:** Ob Liquidsoap direkt per SMB lesen kann, oder ob das Modul die Datei als HTTP-Quelle hinreicht. Vorgesehen
  ist Letzteres, weil es kein Einbinden und kein root braucht.

**Etappe 3 – Live-Studio:**
- Mikrofon im Browser, per WebRTC oder WebSocket zu Liquidsoap (`input.harbor`).
- Jingle-Tasten, Musik absenken beim Sprechen, Vorhören auf Kopfhörer, „Jetzt läuft“, Wunschliste.
- **Alternative:** Ein Moderator sendet mit seinem eigenen Programm (BUTT, Mixxx, mAirList) an den Live-Zugang des
  Studios.

**Etappe 4 – Auf Sendung:**
- Ziele mit Server, Port, Mount, Typ (Icecast/Shoutcast) und Safe-Eintrag.
- Knopf „Auf Sendung“, Zustand (verbunden, getrennt, Fehlergrund), Sendezeit, automatisch neu verbinden.
- **Offen bei Till bzw. seinem Bekannten:** Zugangsdaten und die Regeln von laut.fm für Live-Sendungen (zum Beispiel ob
  eigene Musik live gespielt werden darf).

**Etappe 5 – Sendeplan:** Wochenraster, Regeln je Zeitfenster (Genre, Jahrzehnt, Playlist), Sondersendungen.

## Entscheidungen (Till, 26.10.2026)

1. **mutagen kommt fest in den Kern** (`core/pyproject.toml`). Das ist ein eigener kleiner Kern-PR vor Etappe 1, damit
   jedes Update es mitbringt.
2. **Erstes Einlesen gemütlich:** ein Strang, etwa 3 h.
3. **Name:** „Radiostream“, Modul-ID `radiostream`.
4. **Hörer-Seite:** Port 8800, Standard-Erreichbarkeit „Alle“. Firewall und Fritzbox richtet Till selbst ein.

**Hinweis:** Hörer aus dem Internet über den eigenen Port machen den Server selbst zu einem öffentlichen Sender. Die
Lizenz von My-Hitradio24 gilt für deren Sendung bei laut.fm (Etappe 4), nicht automatisch für diesen Port. Was über
8800 öffentlich läuft, verantwortet Till.
