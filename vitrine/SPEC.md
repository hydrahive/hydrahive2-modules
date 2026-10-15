# Vitrine — Gehäuse-Display als Wohnzimmer-Bühne

**Stand:** 15.10.2026 · **Status:** freigegeben (Till, 15.10.2026) · **Ziel-Host:** hhmaster (192.168.178.226)

## Was

Das 15,6"-Display im Cooler Master MasterFrame 360 Stage LCD steht hochkant hinter einem kleinen Regal mit zwei Spots.
Figuren davor werden Teil der Szene. Vitrine macht daraus eine lebende Bühne:

- **Hintergrund:** kurze, in Schleife laufende Filmchen (Jahreszeiten, Feiertage, besondere Tage), automatisch nach Kalender.
- **Davor (Overlay):** Datum, Uhrzeit, Hydra-Systemstatus.
- **Einblendungen:** Ereignisse (Fehler, Aktionen, Butler-Ereignisse) und Nachrichten von Agenten bzw. Till.

## Warum

Persönliche Deko für Tills Wohnzimmer. Das Gerät gibt es nur an diesem einen Rechner, deshalb als **Modul** (nicht Kern):
installierbar, wenn die Hardware da ist; für alle anderen unsichtbar.

## Hardware (gemessen 15.10.2026, nicht angenommen)

| | |
|---|---|
| USB | ArtInChip USB Device, `33c3:0e02`, High Speed; IF0 vendor-spezifisch (Bulk 0x01/0x81), IF1 Mass Storage |
| Panel | meldet `1080x1920 @ 60 fps`, `ver=5 chip=0x80 fmt=16` — **hochkant eingebaut**, keine Drehung nötig (Till bestätigt) |
| Durchsatz | Video 1080×1920 + Text-Overlay → JPEG Q80 → USB: **~60 fps**, ~17 ms/Frame (davon ~10 ms USB), JPEG Ø 131 KB |
| Verhalten | ohne Host spielt die Firmware eigene Inhalte und meldet sich nur kurz am USB an; sobald der Host Frames schickt, bleibt es stabil |

**Protokoll** (nur Wissen übernommen, kein Code): öffentlich dokumentiert von
[PolybiusPro/MSI-P13-Control](https://github.com/PolybiusPro/MSI-P13-Control) (`docs/protocol-display.md`, GPL-3.0) und
[hevnsnt/artinchip-linux](https://github.com/hevnsnt/artinchip-linux) (MIT):
Vendor-Control `GET_PARAMS` → RSA-PKCS#1-Challenge (`AUTH_DEV`/`AUTH_HOST`) → JPEG-Frames mit 20-Byte-Kopf (`0xA1C62B01`).
Der RSA-**Public**-Key stammt aus Artinchips `aic-render` und ist im MIT-Projekt veröffentlicht; Vitrine bringt ihn mit Quellenangabe mit.
Vitrine-Code wird **neu geschrieben** (keine Übernahme von GPL-Code), Quellen in `vitrine/UPSTREAM.md`.

## Wie (grob)

### Bausteine

1. **Renderer-Dienst** (`has_service: true`, eigener systemd-Dienst `hydrahive2-vitrine`, läuft als `hydrahive`)
   - eigener Prozess, damit das Bild weiterläuft, wenn HydraHive neu startet (Update) — nur Einblendungen pausieren dann
   - eigene venv im Modul-Datenverzeichnis (`pyusb`; Pillow und cryptography wie der Kern), Python wie der Kern (Muster OpenTor)
   - Videos per `ffmpeg` dekodieren (rawvideo-Pipe), Overlay mit Pillow, JPEG, USB
   - Ziel 30 fps (60 möglich, 30 reicht für Deko und spart CPU/USB)
   - verbindet sich selbst neu, wenn das Display neu anmeldet (Reset, Firmware-Wechsel)
   - Nachtmodus: Zeitfenster und Verhalten (dunkel = nur Uhr gedimmt auf Schwarz, oder aus = schwarzes Bild) in den Modul-Einstellungen; Firmware-Helligkeit bleibt bei den Knöpfen
   - spricht nur lokal: Unix-Socket `/run/hydrahive2-vitrine.sock` (nur `hydrahive`), kein Netz-Port
2. **Modul-Backend** (im HydraHive-Prozess)
   - Routen fürs Cockpit: Status, Vorschau-Bild, Videos (Upload/Liste/Löschen), Kalender, Einstellungen, „Nachricht senden“
   - Agenten-Werkzeug **`display_message`** (Text, Dauer, Stil info/erfolg/warnung/fehler) — standardmäßig aus, pro Agent freischaltbar
   - Job: alle 30 s Hydra-Status sammeln (Kern-intern, kein Token nötig) und an den Dienst schicken
   - Butler-Aktion **„Auf Vitrine anzeigen“**, damit Flows Ereignisse einblenden können
3. **Cockpit-Seite „Vitrine“** (nur Admin)
   - Live-Vorschau (zuletzt gerendertes Bild), Videos verwalten, Kalender-Regeln, Testnachricht
   - Einstellungen: Nachtmodus (an/aus, von–bis, „dunkel“ oder „aus“), Bildrate, Dauer der Einblendungen

### Kalender-Regeln

Eine Regel = Zeitraum + Video(s) + Priorität. Höchste passende Priorität gewinnt, bei Gleichstand zufällig im Wechsel.

| Typ | Beispiel |
|---|---|
| Jahreszeit | Frühling 20.03.–20.06. |
| fester Tag/Zeitraum | 24.–26.12. Weihnachten, 31.12.–01.01. Silvester |
| beweglicher Feiertag | Ostern ± Tage, Pfingsten (aus dem Osterdatum berechnet) |
| Tageszeit | 06–10 Uhr Morgen-Variante, 22–06 Uhr Nacht |
| Standard | wenn sonst nichts passt |

### Layout (hochkant 1080×1920)

- oben: Uhrzeit groß, Datum, Feiertagsname wenn vorhanden
- unten: schmale Status-Leiste (Hydra ok/Fehler, CPU, RAM, GPU-Temperatur, laufende Agenten)
- Einblendungen: Karte gleitet unten über der Leiste ein, bleibt *n* Sekunden, Fehler bleiben bis bestätigt oder 10 min
- alles halbtransparent, damit das Video durchscheint; Schriftgröße so, dass sie vom Sofa lesbar ist

### Videos

- Format 1080×1920 hochkant (9:16), MP4/H.264; andere Größen werden beim Abspielen eingepasst
- Herkunft: Atelier (`generate_video`, 9:16) oder Upload
- Ablage im Modul-Datenverzeichnis, `persistent_paths` für Updates

## Bewusst nicht (V1)

- kein Zweitmonitor für den KDE-Desktop (EVDI) — eigenes Thema
- keine Steuerung über die Display-Knöpfe (Firmware behält sie)
- keine Firmware-Updates des Displays
- kein Ton, keine Lampen/Home-Assistant-Aktionen bei Nachrichten (nur Bild; später ausbaubar)

## Sicherheit

- Cockpit-Routen und Werkzeug nur mit Freigabe `module.vitrine` (Standard `admin_only`)
- `display_message`: Text wird gekürzt (≤ 280 Zeichen), keine Bilder/URLs aus Agenten in V1; Secrets-Schwärzung wie bei anderen Ausgaben
- Upload: nur Video-Containerformate, Größenlimit, Dateiname neu vergeben, Prüfung mit `ffprobe`
- Dienst ohne Netz-Port, Socket nur für `hydrahive`; USB-Zugriff per udev-Regel nur für Gruppe `hydrahive` auf `33c3:0e02`

## Etappen

1. **E1 Dienst:** udev, Dienst, Wiederverbinden, Video in Schleife, Uhr/Datum, Status-Leiste (Daten zunächst lokal: CPU/RAM/GPU) — Abnahme am Gehäuse
2. **E2 Kalender + Cockpit:** Regeln, Feiertage, Video-Verwaltung, Vorschau, Nachtmodus
3. **E3 Einblendungen:** Hydra-Status aus dem Kern, `display_message`, Butler-Aktion, Fehler-Ereignisse

## Akzeptanzkriterien

- Nach Neustart des Rechners zeigt das Display binnen 60 s Video + Uhr, ohne Zutun
- HydraHive-Neustart: Video läuft weiter, Status zeigt „Hydra neu startet“ statt einzufrieren
- Display vom USB gezogen/neu gesteckt: Dienst verbindet sich selbst wieder
- 24.12. zeigt das Weihnachtsvideo, 25.12. auch, 27.12. wieder die Winter-Regel (Test mit festem Datum)
- `display_message` von einem Agenten erscheint binnen 2 s und verschwindet nach der Dauer
- CPU-Last des Dienstes bei 30 fps < 10 % eines Kerns (gemessen)

## Entscheidungen (Till, 15.10.2026)

1. Name: **Vitrine**.
2. Nachtmodus: **einstellbar** in den Modul-Einstellungen (Zeitfenster + dunkel/aus), kein fester Standard außer „aus“ bis Till es setzt.
3. Nachrichten: **nur Bild**; Ton/Lampe (Home Assistant) ist ein möglicher Ausbau nach V1.
