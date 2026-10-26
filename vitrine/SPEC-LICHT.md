# Vitrine S8 — Mainboard-Beleuchtung als Statusanzeige (freigegeben von Till am 26.10.2026)

## Was

Die Beleuchtung des Mainboards der .2 wird ein zweiter „Bildschirm“ der Vitrine: Statt dauernd die Farbe zu wechseln,
zeigt sie ruhig an, wie es Hydra gerade geht. Nachts ist sie aus. Die Daten hat die Vitrine schon (Hydra-Status, Meldungen,
Nachtmodus, Kalender); neu ist nur, sie auch ans Licht zu geben.

## Warum

Till, 26.10.2026: „Die leuchtet nachts extrem hell und wabbert nur in verschiedenen Farben – vielleicht als Statusanzeige.“

## Gemessen (26.10.2026 auf .2, nicht angenommen)

- Board **Gigabyte B850 AORUS ELITE X3D**, Licht-Chip **ITE IT5711** am USB (`048d:5711`, Firmware V1.0.09.C), zwei
  HID-Schnittstellen `/dev/hidraw0` + `/dev/hidraw1`; OpenRGB nutzt `hidraw1`.
- **OpenRGB** aus dem Ubuntu-Archiv (`openrgb 0.9+git20251009+ds-1`, universe, GPL-2.0-or-later) erkennt das Board.
  Installation mit `--no-install-recommends`: 6 Pakete, nichts aktualisiert oder entfernt. Das Paket bringt einen
  Benutzer-Dienst `openrgb.service` mit, der **nicht** eingeschaltet ist, und eine udev-Regel (`uaccess` – nur für
  angemeldete Nutzer, also nicht für den Dienstnutzer `hydrahive`).
- Modi laut Board: Direct, Static, Breathing, Flashing, Color Cycle, Double Flash, Wave, Random, Wave 1–4.
  Zonen: Motherboard, 12V RGB Strip, ARGB_V2_1–4 (laut Till hängt dort derzeit nichts).
- Befehl `openrgb --noautoconnect -d 0 -m static -c FF0000` ändert das Licht, **ein Aufruf dauert ~1,2 s**
  (Gerätesuche bei jedem Start). Rot, blau atmend und aus kamen bei Till an (18:14).
- Als `hydrahive` geht es, wenn der Nutzer per ACL auf `hidraw0/1` darf (`setfacl -m u:hydrahive:rw`): `-l` findet das
  Board, Setzen rc 0. Ohne Recht findet OpenRGB nichts (keine Fehlermeldung, nur leere Liste). Test wieder zurückgenommen.
- Danach ist das Licht **aus**. Ob das Board die Einstellung über einen Neustart behält, ist **nicht** geprüft.

## Wie

### Lichtzustände

Die Vitrine entscheidet alle 2 s, welcher Zustand gilt. Wichtigster zuerst:

| Zustand | Wann | Vorgabe (alles im Cockpit änderbar) |
|---|---|---|
| **Aus** | Nachtmodus aktiv (gleiches Zeitfenster wie das Display, abschaltbar) oder Licht im Cockpit ausgeschaltet | aus |
| **Fehler** | ungelesene Meldung der Art `error` | rot; die ersten 20 s blinkend, danach stehend bis „Gelesen“ bzw. bis sie aus dem 24-h-Verlauf fällt |
| **Wartet auf dich** | ungelesene Meldung der Art `warning` | gelb, stehend |
| **Fertig** | ein Agent war aktiv und ist fertig (Agenten-Zahl fällt auf 0) | grün, 5 s – **Vorgabe aus**, einschaltbar |
| **Hydra arbeitet** | mindestens ein Agent läuft (`hydra.json` → `agents > 0`) | blau, atmend |
| **Anlass** | eine Kalenderregel mit eigener Lichtfarbe ist aktiv (Halloween, Advent, Weihnachten …) | Farbe der Regel |
| **Jahreszeit** | sonst | Frühling hellgrün, Sommer warmweiß, Herbst bernstein, Winter kühlweiß |

- Meldungen der Art `info` ändern das Licht nicht.
- „Hydra arbeitet“ steht **unter** Fehler/Warnung: Ein offener Fehler wird nicht von blauem Atmen verdeckt.
- Ist `hydra.json` älter als 2 min (HydraHive läuft nicht), gilt der Ruhe-Zustand (Anlass/Jahreszeit), kein falsches
  „arbeitet“.
- **Anlass** wirkt auch ohne Video: Für das Licht zählt jede passende, eingeschaltete Regel mit Lichtfarbe (höchste
  Priorität gewinnt, gleiche Priorität → erste in der Liste). Die Vorlagen bekommen Vorschläge (Halloween orange,
  Advent warmes Gold, Weihnachten rot, Silvester weiß blinkend, Ostern hellgelb, Valentinstag rosa, St. Martin
  bernstein …); bestehende Regeln haben keine Lichtfarbe, bis Till eine setzt.

### Einstellungen (Till: „so viel wie möglich im Admin steuern“)

Alles in der Vitrine-Seite im Cockpit, Karte **Beleuchtung**:

- **Beleuchtung steuern** an/aus. Aus = die Vitrine fasst das Licht nicht an.
- **Helligkeit** 0–100 %, Vorgabe **80 %** (Till: „kann höher sein“).
- **Nachts aus** an/aus (folgt dem Zeitfenster des Nachtmodus).
- Je Zustand (Fehler, Wartet, Fertig, Arbeitet): **Effekt** (stehend, atmend, blinkend, aus), **Farbe**, **Tempo**
  (0–100, nur bei atmend/blinkend), eigene **Helligkeit** (leer = allgemeine).
- Fehler: **Blinkzeit** am Anfang (0–600 s, Vorgabe 20). Fertig: **an/aus** und **Dauer** (2–60 s, Vorgabe 5).
- **Jahreszeiten:** je eine Farbe und ein Effekt für Frühling, Sommer, Herbst, Winter; Schalter „Jahreszeit-Farben“
  (aus = eine feste Ruhe-Farbe).
- **Anlässe:** im Regel-Editor je Regel ein optionales Feld **Lichtfarbe** + **Effekt**.
- **Vorschau:** Knopf je Zustand – setzt das Licht 15 s darauf, danach zurück.
- Anzeige: gefundenes Gerät, aktueller Zustand (mit Farbe), letzter Fehler.

### Helligkeit

- OpenRGB nimmt `-b 0–100` für alle Effekte an (Quelle: OpenRGB `RGBController_GigabyteRGBFusion2USB.cpp`, alle Modi
  mit `MODE_FLAG_HAS_BRIGHTNESS`; „Breathing“ höchstens 100 wegen einer Eigenheit des Chips). OpenRGB prüft den Wert
  **nicht** (`-b 150` gab rc 0, am 26.10. getestet) → die Vitrine begrenzt selbst auf 0–100.
- Ob der IT5711 die Helligkeit sichtbar umsetzt, prüft Till bei der Abnahme. Falls nicht: Farbe selbst abdunkeln.

### Wie das Licht gesetzt wird

- Eigener Thread im Vitrine-Dienst (wie Bluetooth, S7). **Fehler dort stoppen das Display nie.**
- Er ruft `openrgb` mit festen Argumenten auf (Gerät, Modus, Farbe, Helligkeit). Keine Werte aus der Oberfläche
  ungeprüft in die Befehlszeile: Farben nur `^[0-9A-F]{6}$`, Modi nur aus einer festen Liste, Helligkeit 0–100.
- **Nur bei Änderung** wird gesetzt (ein Aufruf ~1,2 s); dazu einmal alle 10 min der aktuelle Zustand neu (falls das Board
  nach Standby/Neustart in sein Werks-Wabern zurückgefallen ist).
- OpenRGB läuft **ohne** eigenen Server (`--noautoconnect`, kein `--server`) und mit eigenem Konfig-Ordner im
  Vitrine-Datenordner (`<daten>/openrgb`), damit es nichts unter `$HOME` anlegt (Dienst hat `ProtectHome=read-only`).
- Wird das Board nicht gefunden (OpenRGB fehlt, kein Recht, anderes Board): Licht-Thread meldet das einmal im Cockpit
  („Beleuchtung nicht gefunden“) und versucht es alle 5 min neu. Sonst nichts.

### Installer

- `apt-get install --no-install-recommends openrgb` nur, wenn ein bekannter RGB-Chip am USB hängt (`048d:5711`, später
  erweiterbar) und Licht nicht abgeschaltet ist. Sonst nichts installieren.
- udev-Regel (eigene Datei `/etc/udev/rules.d/72-hydrahive2-vitrine-licht.rules`): Für `hidraw` mit `048d:5711` bekommt
  die HydraHive-Gruppe Lese- und Schreibrecht. Nur dieses Gerät, sonst nichts.
- Deinstallation entfernt die Regel. OpenRGB selbst bleibt installiert (ist ein normales Systempaket; andere könnten es
  nutzen) – entfernen nur auf Tills Wunsch.
- Der Benutzer-Dienst `openrgb.service` aus dem Paket bleibt aus.

### Cockpit

Siehe „Einstellungen“ oben (Karte **Beleuchtung** auf der Vitrine-Seite, Lichtfarbe im Regel-Editor).

### Nicht in S8

- Keine Zonen einzeln (Lüfter/Streifen), nur das ganze Board – solange dort nichts hängt.
- Kein OpenRGB-Server, keine Steuerung über das Netz, keine Effekte im Takt der Videos.
- Keine Grafikkarte/RAM (bräuchte i2c-dev/SMBus; OpenRGB meldet die Warnung, für das Mainboard am USB unwichtig).

## Sicherheit

- Der Vitrine-Dienst darf nur auf dieses eine USB-Gerät (udev-Regel nach Hersteller + Produkt).
- Keine freien Werte in Shell-Befehlen; `subprocess` mit Argumentliste, nie `shell=True`.
- Kein offener Port (kein OpenRGB-Server – dessen Standard wäre 0.0.0.0:6742, ohne Anmeldung).

## Akzeptanz

- Nach der Installation wechselt das Licht nicht mehr selbst die Farbe; tagsüber Ruhe (warmweiß gedimmt).
- Agent läuft → binnen 10 s blau atmend; fertig → zurück (bzw. 5 s grün, wenn eingeschaltet).
- Fehler-Meldung → rot blinkend, nach 20 s rot stehend; „Gelesen“ → binnen 10 s zurück.
- Nachtmodus-Zeitfenster → Licht aus; danach wieder an.
- Am 31.10. (Regel Halloween mit Lichtfarbe) → orange; am 01.11. Herbst-Farbe (Test mit festem Datum).
- Jede Einstellung im Cockpit wirkt binnen 10 s; ungültige Werte lehnen Server und Browser ab.
- Schalter „Beleuchtung steuern“ aus → die Vitrine setzt nichts mehr.
- OpenRGB fehlt / Board nicht gefunden → Display läuft unverändert, Cockpit zeigt „Beleuchtung nicht gefunden“.
- Last: Licht-Thread im Mittel < 1 % eines Kerns (Aufruf nur bei Änderung).
- Tests: Zustands-Wahl (Reihenfolge), Befehlszeile (feste Argumente, Prüfung der Farben), nur bei Änderung, Wiederholen
  alle 10 min, Fehler stoppen den Dienst nicht, Schema, Installer-Regel nur für `048d:5711`.

## Entscheidungen (Till, 26.10.2026)

1. Bauen wie vorgeschlagen (Farben je Zustand).
2. Helligkeit höher als 30 % und im Admin einstellbar → Vorgabe 80 %.
3. Farben nach Jahreszeit und Anlass, im Admin einstellbar.
4. „So viel wie möglich im Admin steuern lassen.“
Nicht ausdrücklich beantwortet, daher einstellbar mit vorsichtiger Vorgabe: „Fertig“ kurz grün (Vorgabe aus),
Ruhe = Jahreszeit-Farbe (abschaltbar → feste Ruhe-Farbe oder Effekt „aus“).
