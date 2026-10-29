# Radiostream – Bauplan Etappe 2: Sendebetrieb und Hörer-Seite

> Status: **Plan.** Gebaut wird erst nach Tills Freigabe. Grundlage: `SPEC.md` (Abschnitte „Aufbau“, „Hörer-Seite“,
> „Spätere Etappen – Etappe 2“). Stand 29.10.2026, Bibliothek auf dem Hauptserver vollständig: 175.462 Titel,
> 0 Fehler, rund 498 Tage Musik.

## Ziel

Rund um die Uhr läuft ein Programm aus der eigenen Sammlung. Man hört es über eine eigene, schlichte Hörer-Seite auf
Port 8800, ohne HydraHive-Konto. Im Modul sieht man „Jetzt läuft“, die nächsten Titel und die Hörerzahl. Man kann den
Sender starten und stoppen.

## Befund (29.10.2026, nur gelesen)

| | Hauptserver (.2) | hydratest |
|---|---|---|
| System | Ubuntu 26.04.1 | Ubuntu 24.04.5 |
| `liquidsoap` (apt) | 2.4.0 | 2.2.4 |
| `icecast2` (apt) | 2.5.0 | 2.4.4 |
| installiert | nein | nein |

- Beide Pakete gibt es in `universe`. Liquidsoap 2.2 und 2.4 unterscheiden sich in Kleinigkeiten. Das Skript nutzt nur
  Funktionen, die es in beiden gibt (`request.dynamic`, `crossfade`, `normalize`, `output.icecast`). Die Probe läuft auf
  beiden Ständen.
- Dienste mit `has_service` richtet das Modul über `extension/install.sh` mit `sudo -n bash` ein, wie bei vitrine.
- nginx hat schon `hydrahive2` (80/443) und `gitea` (3001). Port 8800 ist frei.
- Auf .2 gibt es keine Firewall vor neuen Ports (INPUT ACCEPT). Die Adressregel in nginx ist die eigentliche Schranke.

## Aufbau

```
Modul (Python, HydraHive-Backend)                    Liquidsoap (Dienst)              Icecast (Dienst)
 rotation.py  – wählt den nächsten Titel   ◀── fragt ──  request.dynamic          ──▶  127.0.0.1:8810/radio.mp3
 feed routes  – /feed/next, /feed/file/<id>  ── liefert ▶ (HTTP, mit Feed-Schlüssel)       │
 control.py   – Dienste an/aus, Status                                                    ▼
 listener_site.py – erzeugt die Hörer-Seite + nginx-Block  ──▶  nginx :8800  /  /stream  /jetzt
```

### Neue Teile

1. **`extension/install.sh` / `uninstall.sh`** (`has_service: true`):
   - Installiert `liquidsoap` und `icecast2` mit `--no-install-recommends`. Bei icecast2 wird die debconf-Frage
     vorbelegt, damit nichts nachfragt.
   - Legt eigene Dienste an:
     - `hydrahive-radiostream-icecast`: eigene Konfiguration unter `/etc/hydrahive2/radiostream/icecast.xml`,
       **nur 127.0.0.1:8810**, Benutzer `hydrahive`. Der Paket-Dienst `icecast2` bleibt aus.
     - `hydrahive-radiostream-liquidsoap`: Skript `/var/lib/hydrahive2/radiostream/radio.liq`, Benutzer `hydrahive`.
   - Erzeugt Passwörter (Quelle, Admin, Feed-Schlüssel) einmalig in `/etc/hydrahive2/radiostream/secrets.env`, 0600,
     Besitzer hydrahive. Bei einem Update bleiben sie gleich.
   - Startet die Dienste **nicht von selbst**. Gesendet wird erst, wenn man im Modul „Sender starten“ drückt.
   - `uninstall.sh` stoppt und entfernt Dienste und den nginx-Block. Die Pakete bleiben, die Bibliothek ebenso.
2. **Rotation (`rotation.py`)**: Das Modul wählt den nächsten Titel:
   - nur Titel mit `state = ok`;
   - **gleicher Künstler frühestens nach 60 min**, **gleicher Titel frühestens nach 3 Tagen** (einstellbar);
   - Zufall gewichtet. Findet sich nichts Passendes, werden die Sperren schrittweise gelockert, damit nie Stille
     entsteht;
   - Gespielt-Liste in einer eigenen Tabelle `module_radiostream_plays` (Titel, Zeit), 30 Tage aufbewahrt.
3. **Zuspielung an Liquidsoap (`feed`-Routen)**:
   - `GET /api/modules/radiostream/feed/next`: gibt die URL des nächsten Titels zurück und trägt ihn als gespielt ein.
   - `GET /api/modules/radiostream/feed/file/<track_id>`: liefert die Datei vom NAS als Strom. MP3 und FLAC gehen
     unverändert durch, Liquidsoap dekodiert selbst.
   - **Nur mit Feed-Schlüssel** (Kopfzeile) und **nur von 127.0.0.1**. Ohne Schlüssel kommt 403. Der Schlüssel öffnet
     nichts anderes.
4. **Liquidsoap-Skript** (aus einer Vorlage im Modul erzeugt):
   - `request.dynamic` → `normalize` (gleiche Lautheit) → `crossfade` (3 s, Stille am Ende abschneiden) →
     `output.icecast` MP3 192k.
   - Bei einem Fehler (NAS kurz weg) springt es zum nächsten Titel. Ist gar nichts zu bekommen, läuft eine leise
     Notschleife statt Stille.
5. **Hörer-Seite (`listener_site.py`)**, wie in `SPEC.md` beschrieben:
   - Erzeugt statische Dateien unter `/var/lib/hydrahive2/radiostream/public/` (HTML, CSS, kleines JS, Logo) und den
     nginx-Block `/etc/nginx/sites-available/hydrahive-radiostream`.
   - **Nur drei Wege:**
     - `/`
     - `/stream` (auch `/stream.mp3` und `/stream.m3u`)
     - `/jetzt`: Icecast-Status, gefiltert auf Künstler und Titel.
   - Alles andere ergibt 404. Es gibt keinen Weg zu 8001 und kein `/api`.
   - Vor dem Neuladen läuft `nginx -t`. Bei einem Fehler bleibt die alte Fassung.
   - Erreichbarkeit „Alle“ (Standard), „Heimnetz und Tailscale“ oder „Aus“.
   - Höchstens 50 Hörer und eine Verbindungsgrenze je Adresse.
   - `Content-Security-Policy: default-src 'self'`.
6. **Studio-Oberfläche, Reiter „Sender“** (nur Admins steuern, alle sehen):
   - „Jetzt läuft“, die nächsten 3 Titel, die zuletzt gespielten 10;
   - Hörerzahl (aus dem Icecast-Status, ohne Adressen);
   - Knöpfe „Sender starten“, „Sender stoppen“ und „Titel überspringen“;
   - Einstellungen:
     - Sendername und Untertitel
     - Künstler- und Titelsperre
     - Erreichbarkeit und Port
     - Höchstzahl Hörer
   - Link zur Hörer-Seite. Hinweis bei „Alle“: „Den Port im Router freigeben musst du selbst.“
   - Kein Wort von Liquidsoap, Icecast oder nginx in der Oberfläche.

### Rechte

- Sender starten, stoppen und Einstellungen ändern dürfen nur Admins. Neue Freigabe `radiostream.control`, voreingestellt
  `admin_only`.
- Sehen, was läuft, dürfen alle mit `module.radiostream`.
- Die Feed-Routen haben keine Benutzer-Anmeldung, nur den Feed-Schlüssel und die Adresse 127.0.0.1.

### Fehlercodes (de/en)

`radiostream_service_missing` (Dienste nicht eingerichtet), `radiostream_service_failed` (startet nicht),
`radiostream_library_empty` (nichts zu spielen), `radiostream_port_invalid`, `radiostream_port_in_use`,
`radiostream_nginx_failed` (Konfiguration abgelehnt, alte bleibt), `radiostream_feed_forbidden`.

## Prüfung

- Rote Tests zuerst. Rotation:
  - Sperren für Künstler und Titel greifen;
  - gelockert wird nur, wenn nichts passt;
  - `missing` wird nie gewählt.
- Feed:
  - ohne Schlüssel oder von außen 403;
  - Datei läuft als Strom;
  - Schlüssel nie in Antworten.
- nginx-Block:
  - nur die drei Wege, kein 8001, kein `/api`;
  - Adressregeln je Erreichbarkeit stimmen;
  - `max_conns`/`limit_conn` gesetzt.
- Hörer-Seite: keine fremden URLs, CSP gesetzt.
- Mutanten bis keiner überlebt, Gegenprobe gegen `main`.
- **Probe auf hydratest:**
  - Modul-Update installiert die Pakete;
  - Sender starten → nach höchstens 10 s Ton auf `http://<hydratest>:8800/stream`, mit ffprobe geprüft;
  - 30 min Dauerlauf: mindestens 6 Titelwechsel, keine Wiederholung, Überblendung hörbar (Stichprobe von Till);
  - `/api/health` über 8800 → 404;
  - `/admin` über 8800 → 404;
  - NAS kurz unerreichbar (Route sperren) → nächster Titel bzw. Notschleife, danach wieder normal.
- E2E der Sender-Seite bei 1600, 1280, 393 und 375 px. Die Hörer-Seite zusätzlich am Handy.
- Danach erst Hauptserver (Modul-Update durch Till).

## Nicht in Etappe 2

- Live-Mikrofon und Jingles (Etappe 3)
- externe Ziele wie laut.fm (Etappe 4)
- Sendeplan nach Uhrzeit (Etappe 5)
- Wünsche und Bewertungen
- AAC als zweiter Stream (kann später dazu)

## Fragen an Till

1. **Hörer-Port 8800 und „Alle“** wie am 26.10. entschieden, oder für den Anfang erst „Heimnetz und Tailscale“, bis du
   den Router freigegeben hast?
2. **Sendername** für die Hörer-Seite?
3. **Sperren** 60 min Künstler und 3 Tage Titel so lassen?
