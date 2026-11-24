# M0 – Machbarkeit Vitrine mit zwei Arbeitsplätzen (ziele/vitrine-multiseat.md, MS1)

**Datum:** 24.11.2026, 16:44–17:06, Server hydrahive-master (Ubuntu 26.04, Xorg 21.1.22, sddm 0.21, amdgpu 25.0.0,
nvidia 580.178.04 open, evdi aus Ubuntu-Kernel 7.0.0-44). Till vor den Bildschirmen, Freigabe „du kannst alles machen“.
Jede Probe mit vorab gestartetem Rückbau-Timer (systemd-run, 4 min). Danach Ursprungszustand belegt (ein Arbeitsplatz,
keine 72-seat-Regeln, keine Probe-Dateien, Kiosk läuft, DVI-I primary 1080x1920).

## Ausgangslage (vor den Proben)
Ein Arbeitsplatz. Xorg nutzt die **NVIDIA als Hauptgrafik** (Provider 0 „Source Output“), AMD und EVDI als „Sink“.
Das Kiosk-Skript koppelt EVDI mit `xrandr --setprovideroutputsource <modesetting> 0` an Provider 0 = NVIDIA.
Der Fernseher (HDMI-0) hängt am selben Xorg und wird vom Kiosk-Skript abgeschaltet.
→ Erklärt den Fehlschlag vom 24.11. 16:26: Vitrine wurde auf AMD gelegt, EVDI war nicht mehr gekoppelt.

## Proben
| Probe | Aufbau | Ergebnis |
|---|---|---|
| A | nur AMD (BusID) im Xorg, ein Arbeitsplatz | Xorg läuft auf AMD, **EVDI nicht eingebunden** (1 Provider, keine Ausgänge) |
| B/C | `loginctl attach seat1` NVIDIA + HDMI-Ton, keine Xorg-Datei | seat1 (NVIDIA, HDMI-0 3840x2160) läuft; **seat0 startet nicht**: `Cannot run in framebuffer mode. Please specify busIDs for all framebuffer devices` (Xorg-seat0-m0c-fehler.log) |
| D | wie B + seat0-Xorg-Datei mit AMD-BusID (MatchSeat seat0) | seat0 läuft auf AMD, **EVDI fehlt** (feste BusID → keine automatische Zusatz-GPU) |
| **E** | wie D + EVDI als `Device` (modesetting, `kmsdev /dev/dri/card1`) und `GPUDevice` im Screen (xorg-seat0-m0e.conf) | **seat0: AMD + EVDI, `DVI-I-1-1 connected primary 1080x1920`, Kiosk-Firefox läuft, Bildschirmfoto zeigt das Dashboard (seat0-m0e.png). seat1: NVIDIA, HDMI-0 3840x2160.** |

## Folgerungen für M1/M2
1. Vitrine-Arbeitsplatz braucht eine Xorg-Datei mit `MatchSeat "seat0"`: Haupt-GPU per BusID + EVDI als `GPUDevice`
   (Driver modesetting, Option kmsdev = EVDI-Gerät). BusID und kmsdev aus dem System ermitteln, nie fest.
   Der EVDI-Ausgang heißt dann `DVI-I-1-1` (vorher `DVI-I-2-1`) → kiosk-session.sh sucht schon nach `^DVI-I-[0-9-]+`.
2. Die Haupt-GPU des Vitrine-Arbeitsplatzes ist eine andere Karte als die des zweiten Arbeitsplatzes. Gibt es nur eine
   echte GPU, geht Multiseat nicht (Vorschlag darf dann nicht angeboten werden).
3. **sddm meldet den Kiosk-Benutzer auch auf seat1 an** (Probe E: Sitzung hydrahive-kiosk auf seat1) – belegt die
   Notwendigkeit von lightdm mit `[Seat:seat0] autologin-user` und Anmeldebildschirm auf seat1.
4. Gerätezuordnung über `loginctl attach seat1 <sysfs>` legt `/etc/udev/rules.d/72-seat-*.rules` an;
   `loginctl flush-devices` entfernt sie wieder (Rückbau belegt).
5. Nicht geprüft: Ton am Fernseher, Eingabegeräte an seat1 (Rapoo), lightdm, Neustart des Rechners.
