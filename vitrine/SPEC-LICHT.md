# Vitrine S8 — Mainboard-Beleuchtung als Statusanzeige (Entwurf, wartet auf Tills Freigabe)

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

Die Vitrine entscheidet alle paar Sekunden, welcher Zustand gilt. Wichtigster zuerst:

| Zustand | Wann | Standard |
|---|---|---|
| **Aus** | Nachtmodus aktiv (gleiches Zeitfenster wie das Display) oder Licht im Cockpit ausgeschaltet | aus |
| **Fehler** | ungelesene Meldung der Art `error` (z. B. aus `errors_log`) | rot, blinkt 20 s, danach rot stehend bis „Gelesen“ bzw. bis sie aus dem 24-h-Verlauf fällt |
| **Wartet auf dich** | ungelesene Meldung der Art `warning` | gelb stehend |
| **Hydra arbeitet** | mindestens ein Agent läuft (`hydra.json` → `agents > 0`) | blau atmend |
| **Anlass** | eine Kalenderregel mit Lichtfarbe ist aktiv (z. B. Halloween, Advent) | Farbe der Regel, stehend |
| **Ruhe** | sonst | warmweiß, gedimmt |

- Meldungen der Arten `info`/`success` ändern das Licht nicht (sonst blinkt es bei jedem Kleinkram).
- „Hydra arbeitet“ steht absichtlich **unter** Fehler/Warnung: Ein offener Fehler soll nicht durch blaues Atmen verdeckt
  werden.
- Ist `hydra.json` älter als 2 min (HydraHive läuft nicht), gilt **Ruhe** – kein falsches „arbeitet“.

### Helligkeit

- Eine Grundhelligkeit für alles (Standard **30 %**), damit das Licht im Wohnzimmer nicht blendet.
- **Gemessen wird beim Bau**, ob der IT5711 im Modus „Static“ die Helligkeit annimmt (`-b`). Wenn nicht, wird die Farbe
  selbst abgedunkelt (z. B. 30 % von FF0000 = 4D0000) – sieht gleich aus.

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

### Cockpit (Vitrine-Seite, neue Karte „Beleuchtung“)

- Schalter **Beleuchtung steuern** (an/aus). Aus = die Vitrine fasst das Licht nicht an (es bleibt, wie es ist).
- **Grundhelligkeit** (0–100 %).
- Farbe je Zustand (Fehler, Wartet, Arbeitet, Ruhe) mit Vorgabe; Kalender-Regeln bekommen ein optionales Feld
  **Lichtfarbe** im Regel-Editor.
- **Zustand prüfen**: Knopf „Vorschau“ je Zustand – setzt das Licht 10 s auf diesen Zustand, danach zurück.
- Anzeige: gefundenes Gerät (Name, Chip), aktueller Zustand, letzter Fehler.

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
- Agent läuft → binnen 10 s blau atmend; fertig → zurück.
- Fehler-Meldung → rot blinkend, nach 20 s rot stehend; „Gelesen“ → binnen 10 s zurück.
- Nachtmodus-Zeitfenster → Licht aus; danach wieder an.
- Schalter „Beleuchtung steuern“ aus → die Vitrine setzt nichts mehr.
- OpenRGB fehlt / Board nicht gefunden → Display läuft unverändert, Cockpit zeigt „Beleuchtung nicht gefunden“.
- Last: Licht-Thread im Mittel < 1 % eines Kerns (Aufruf nur bei Änderung).
- Tests: Zustands-Wahl (Reihenfolge), Befehlszeile (feste Argumente, Prüfung der Farben), nur bei Änderung, Wiederholen
  alle 10 min, Fehler stoppen den Dienst nicht, Schema, Installer-Regel nur für `048d:5711`.

## Offene Fragen an Till

1. **Farben** so lassen (Ruhe warmweiß gedimmt, arbeitet blau atmend, wartet gelb, Fehler rot)?
2. **Grundhelligkeit** 30 % als Start ok?
3. **Info/Erfolg** wirklich ohne Licht – oder z. B. kurz grün (5 s), wenn ein Agent fertig ist?
4. Bei **Ruhe** lieber eine Farbe (warmweiß) oder ganz aus (nur Zustände leuchten)?
