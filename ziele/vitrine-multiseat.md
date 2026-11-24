# Zieldokument: Vitrine auf einem Rechner mit zwei Arbeitsplätzen (Multiseat)

> **Status:** FREIGEGEBEN (Till, 24.11.2026: „ok so machen wir es“ – automatischer Vorschlag, lightdm nur bei zwei
> Arbeitsplätzen, Hinweis bei erkanntem Monitor)
> **Repo:** hydrahive2-modules, Modul `vitrine` (heute 0.17.3)
> **Auslöser:** Till, 24.11.2026: Am Server soll die Vitrine (Gehäuse-Display) laufen UND ein normaler Arbeitsplatz
> am Fernseher (eigene Tastatur/Maus/Ton). Ein Handversuch des Projekt-Agenten am 24.11. 16:26 ist gescheitert
> (Vitrine schwarz, Rückbau von Hand). Till: „lass es uns gleich richtig machen“ – kein Handbau am Server, das Modul
> muss es können, allgemeingültig.

## 1. Ist-Stand (belegt)
**Modul (Code, main):**
- `vitrine/extension/install.sh:38–72` richtet den Kiosk nur ein, wenn **kein echter Monitor** angeschlossen ist
  (Schleife über `/sys/class/drm/card*-*/status`, nicht-EVDI + `connected` → kein Kiosk) und wenn `sddm` da ist.
- `vitrine/extension/kiosk-install.sh:81–99` schreibt `/etc/sddm.conf` neu (`[Autologin] User=…, Relogin=true`)
  und startet sddm unter Umständen neu.
- `install.sh:62` setzt fest `VITRINE_KIOSK_DISPLAY=:0`; `renderer/play_dashboard.py:18–19` braucht es.
- `vitrine/extension/kiosk-session.sh:16–26` schaltet per xrandr **jeden** verbundenen Ausgang außer `DVI-I-*` ab.
**Quellen:**
- sddm (`src/daemon/Display.cpp`, develop, Z. 175–177): Autologin hängt nur an `[Autologin] User`, nicht am
  Arbeitsplatz → gilt für jede Anzeige. Bestätigt den Befund vom 24.11. („Vitrine meldet sich auch am Fernseher an“).
- lightdm (`data/lightdm.conf`, Z. 43–44): Abschnitte `[Seat:seat0]`, `[Seat:<name>]` je Arbeitsplatz →
  Autologin je Arbeitsplatz möglich.
**Server hydrahive-master (24.11. 16:44, nur gelesen):** ein Arbeitsplatz `seat0`; sddm 0.21 aktiv, liegt unter
`/usr/bin/sddm` (nicht `/usr/sbin` – die Rückbau-Anleitung des Agenten war deshalb falsch); lightdm nicht installiert;
Grafik: AMD 0d:00.0 = card0, EVDI = card1 (DVI-I-1, aktiv), NVIDIA 01:00.0 = card2 (HDMI-A-1, aus); Sitzungen
`Lubuntu`, `hydrahive-vitrine-kiosk`, `lxqt`, `openbox`.
**Nicht belegt:** ob Xorg auf seat0 AMD + EVDI zusammen bedienen kann (Versuch 24.11.: EVDI nicht eingebunden →
schwarz). Genau das klärt Etappe M0.

## 2. Zielbild
Ein Admin schaltet in der Vitrine **„Zweiter Arbeitsplatz“** ein. Die Vitrine **schlägt die Zuordnung selbst vor**,
der Admin klickt **„Übernehmen“** und muss nur bei einem falschen Vorschlag etwas ändern:
- **Vorschlag:** Die Grafikkarte mit dem USB-Display (EVDI) und ihre Eingabegeräte bleiben bei der Vitrine (seat0).
  Eine andere Grafikkarte mit verbundenem Bildschirm wird der zweite Arbeitsplatz (seat1), dazu ihr Ton
  (HDMI-Audio derselben PCI-Karte) und die Eingabegeräte, die der Vitrine nicht zugeordnet sind. Grundlage sind die
  Daten des Systems (`/sys/class/drm`, `loginctl seat-status`, `/proc/bus/input/devices`), nichts Festes.
- **Ändern:** eine Liste der Grafikkarten, Eingabegeräte und Tonkarten mit lesbaren Namen und Auswahl „Vitrine“ /
  „Zweiter Arbeitsplatz“.
- **Hinweis ohne Knopfdruck:** Erkennt der Installer beim Installieren/Update einen echten Monitor an einer anderen
  Grafikkarte als dem USB-Display, zeigt die Vitrine „Zweiter Bildschirm erkannt – als eigenen Arbeitsplatz
  einrichten?“ (statt wie heute den Kiosk still nicht einzurichten).

Danach:
- Arbeitsplatz 1 (seat0) zeigt wie heute die Vitrine – automatisch angemeldet, Kiosk.
- Arbeitsplatz 2 (seat1) zeigt einen normalen Anmeldebildschirm; dort meldet sich ein Mensch mit seiner Sitzung an.
- Ein Vitrine-Update ändert daran nichts.
- **„Zweiten Arbeitsplatz ausschalten“** stellt den Zustand von vorher wieder her (ein Arbeitsplatz, sddm, wie heute).
Ohne diesen Schalter verhält sich die Vitrine **genau wie heute** (sddm bleibt, niemand merkt etwas).

## 3. Regeln
- **Kein Handbau am Server.** Alles über den Modul-Installer (root über den vorhandenen Weg `sudo -n bash`), nach
  dem Muster von `kiosk-install.sh`. Geräte-Pfade und Kartennummern werden ermittelt, nie fest eingetragen.
- **Allgemeingültig:** keine Pfade, PCI-Adressen oder Gerätenamen dieses Servers im Code. Referenz Ubuntu 26.04.
- **Sicher umschalten:** Vor jeder Änderung Sicherung der berührten Dateien; automatische Prüfung danach (Vitrine-
  Ausgang aktiv, Kiosk-Firefox läuft, Arbeitsplatz-2-Anmeldung läuft); schlägt sie fehl → **automatischer Rückbau**
  auf den Stand davor, mit Meldung. Der Rückbau wird vorher im Test geprüft, nicht erst im Ernstfall.
- **Display-Manager:** intern, für den Nutzer unsichtbar. Ein Arbeitsplatz → sddm wie heute. Zweiter Arbeitsplatz an
  → der Installer wechselt auf lightdm (sddm kann Autologin nicht je Arbeitsplatz), aus → zurück auf sddm. lightdm wird
  nur dann installiert (Modul-Installer, wie heute schon openbox/evdi), nie für Ein-Arbeitsplatz-Nutzer, nie von einem
  Agenten.
- **Ein Arbeitsplatz bleibt Standard** (überholt durch §7 Nachtrag 24.11.2026); der Fall „echter Monitor angeschlossen → kein Kiosk“ bleibt wie heute, außer
  der Monitor ist ausdrücklich dem zweiten Arbeitsplatz zugewiesen.
- `kiosk-session.sh` schaltet nur Ausgänge **seines** Arbeitsplatzes ab, nie die des zweiten.
- Deutsche Texte; jede Meldung sagt, was der Nutzer tun kann. Hilfe-Artikel der Vitrine wird ergänzt.

## 4. Nicht-Ziele
- Mehr als zwei Arbeitsplätze; Wayland am zweiten Arbeitsplatz; automatisches Erkennen „welche Tastatur gehört wohin“
  ohne Auswahl durch den Admin.

## 5. Etappen
- **M0 Machbarkeit (vor dem Bau, nur Probe, kein Umbau am Server):** In einer Wegwerf-Umgebung oder in einem
  Wartungsfenster MIT Till vor den Bildschirmen: Xorg-Konfiguration für seat0 mit AMD + EVDI finden, die den
  EVDI-Ausgang zeigt (mögliche Wege: `Inactive`/`setprovideroutputsource` wie heute im Kiosk-Skript, oder EVDI ohne
  AMD). Ergebnis mit Logs dokumentieren. **Ohne funktionierende Xorg-Konfiguration kein Bau.**
- **M1** Erkennung + Vorschlag: Zuordnungs-Vorschlag aus den Systemdaten, Liste zum Ändern, Hinweis bei erkanntem
  Monitor; Admin-Oberfläche „Zweiter Arbeitsplatz“ (Anzeige, Vorschlag, Auswahl – noch kein Umschalten).
- **M2** Umschalten im Installer: lightdm + Konfiguration je Arbeitsplatz, `loginctl attach`, Xorg-Datei für seat0,
  Sicherung, Prüfung, automatischer Rückbau; `install.sh`/`kiosk-install.sh` erkennen den Modus und lassen sddm in Ruhe.
- **M3** Kiosk-Sitzung arbeitsplatzbewusst (`kiosk-session.sh`, `VITRINE_KIOSK_DISPLAY` aus der tatsächlichen
  Anzeige von seat0 statt fest `:0`), Hilfe-Artikel, Live-Test am Server mit Till.

## 6. Abnahme-Punkte
| # | Prüfung |
|---|---|
| MS1 | M0 dokumentiert: funktionierende Xorg-Konfiguration für seat0 (AMD + EVDI) mit Befehlen, Logs und Foto/Aussage „Vitrine sichtbar“ – oder begründet „nicht machbar“ |
| MS2 | Ohne Schalter: Vitrine-Installation/Update ändert nichts gegenüber 0.17.3 (Tests vergleichen erzeugte Dateien/Befehle) |
| MS9 | Vorschlag: Aus nachgestellten Systemdaten (zwei Grafikkarten, EVDI, Eingabegeräte, HDMI-Ton) entsteht die richtige Zuordnung; Hinweis „Zweiter Bildschirm erkannt“ erscheint nur bei echtem Monitor an einer Nicht-EVDI-Karte (Tests) |
| MS3 | Mit Schalter: Installer erzeugt lightdm-Konfiguration mit Autologin NUR für seat0 und Anmeldebildschirm für seat1; keine festen Geräte-Pfade im Code (Test) |
| MS4 | Rückbau: Bei fehlgeschlagener Prüfung stellt der Installer den Stand davor her (sddm, Dateien, Gerätezuordnung) – im Test erzwungen und belegt; Pfade nicht geraten (sddm-Pfad aus dem System, nicht fest) |
| MS5 | Update mit Schalter an: sddm wird nicht angefasst, lightdm-Zustand bleibt (Test) |
| MS6 | `kiosk-session.sh` schaltet nur Ausgänge von seat0 ab (Test mit zwei Arbeitsplätzen) |
| MS7 | Live am Server mit Till: Vitrine auf dem Gehäuse-Display, Anmeldebildschirm am Fernseher, Till meldet sich an, Ton am Fernseher; Neustart des Servers → beides wieder da; Schalter aus → Zustand wie vorher |
| MS8 | Hilfe-Artikel der Vitrine beschreibt Schalter, Auswahl, Rückbau; gegen Code geprüft |

## 7. Nachtrag 24.11.2026 – „Vitrine und Desktop immer“ (Till freigegeben)
Till: „vitrine und desktop sollen immer gehen, wenn vitrine installiert ist ist immer ein usb angeschlossen.“
Belegt (Live-Test 1, 18:41/18:54): Mit angeschlossenem Fernseher schreibt jedes Update die Unit ohne Dashboard
(install.sh „Monitor → kein Kiosk“). Die Regel einfach zu streichen geht nicht: Mit EINEM Arbeitsplatz meldet sddm den
Kiosk an und `kiosk-session.sh` schaltet jeden Nicht-EVDI-Ausgang ab → Fernseher schwarz, keine Anmeldung möglich.
Beides gleichzeitig = zwei Arbeitsplätze. Daher, abweichend von §3 „Ein Arbeitsplatz bleibt Standard“:
- **N1** Der Kiosk wird immer eingerichtet; der Zweig „echter Monitor → kein Kiosk“ entfällt.
- **N2** Ist ein echter Monitor an einer anderen Grafikkarte als dem USB-Display angeschlossen und gibt es eine
  gespeicherte, gültige Zuordnung (seats.json), schaltet Installation/Update den zweiten Arbeitsplatz automatisch
  ein – über multiseat-apply.sh mit Sicherung, Prüfung und Rückbau-Timer. Ohne gültige Zuordnung: Vitrine-Kiosk wie
  heute ohne Monitor-Abschaltung des zweiten Bildschirms **nicht** möglich → Kiosk wird eingerichtet, aber
  kiosk-session.sh schaltet fremde Ausgänge NICHT ab, solange ein Monitor erkannt und kein Multiseat aktiv ist
  (Fernseher bleibt nutzbar als gespiegelte/zusätzliche Anzeige), und die Oberfläche zeigt „Zweiter Bildschirm
  erkannt – als eigenen Arbeitsplatz einrichten?“.
- **N3** „Zweiten Arbeitsplatz ausschalten“ bleibt; wer bewusst ausschaltet, wird nicht beim nächsten Update wieder
  eingeschaltet (Vermerk in seats.json: `auto: false`).
- **Reihenfolge:** N1–N3 werden erst gebaut, wenn der zweite Live-Test (0.17.8, Knopf) bestanden ist.

| # | Prüfung |
|---|---|
| MS10 | Update mit angeschlossenem Monitor und gültiger Zuordnung schaltet automatisch ein (Ersatzprogramme); mit `auto: false` nicht; ohne Zuordnung Kiosk ohne Abschalten fremder Ausgänge + Hinweis |
| MS11 | Live: Update auf die neue Version mit Fernseher am Server → Vitrine-Dashboard UND Anmeldebildschirm am Fernseher ohne Klick |
