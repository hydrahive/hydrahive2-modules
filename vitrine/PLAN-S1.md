# Plan Vitrine S1 — Umschalten Video ↔ Dashboard per Maus

Spec: `vitrine/SPEC-STATUSZENTRALE.md` (freigegeben 18.10.2026). S1 baut nur das **Umschalten** mit einer Platzhalter-Seite;
die Statuszentrale (Daten-Route, echte Seite) ist S2.

## 0. Gerätetest am Gehäuse (vor dem Dienst-Code)
Mit dem Testaufbau vom 18.10. (`/opt/vitrine-evdi-test`) prüfen, was S1 voraussetzt. Geht etwas nicht → Stopp, mit Till neu bewerten:
- Kiosk-Sitzung per sddm-Autologin startet in Openbox mit Firefox `--kiosk` auf einer lokalen Seite, **kein** Anmeldebildschirm sichtbar
- Leerlaufzeit des Kiosk-X-Servers (`XScreenSaverQueryInfo`) fällt beim Bewegen des Trackpads auf ~0
- EVDI-Ausgang bleibt nach dem Autologin aktiv (oder lässt sich in der Sitzung mit `xrandr` einschalten)
- Last messen: Firefox auf einer ruhigen Seite + Brücke über 60 s

**Ergebnis Schritt 0 (18.10.2026, am Gehäuse, Till hat Trackpad und Klick bestätigt):**

| Punkt | Ergebnis |
|---|---|
| Autologin mit eigenem Nutzer (gesperrtes Passwort) in eine Openbox-Sitzung | ✔ kein Anmeldebildschirm, kein Benutzername |
| Firefox (Snap) `--kiosk` auf lokaler Seite | ✔ Vollbild ohne Browserleiste |
| EVDI-Ausgang in der Sitzung einschalten (`--setprovideroutputsource` + `--output DVI-I-…`) | ✔ |
| Leerlaufzeit (`XScreenSaverQueryInfo`) | ✔ simulierte und echte Eingabe → 0–300 ms; Klick kommt in der Seite an |
| Last, ruhige Seite mit sekündlicher Uhr, 60 s | Brücke 3,4 % + Firefox 1,1 % eines Kerns |

**Was daraus für den Bau folgt:**
- `/etc/sddm.conf` hat Vorrang vor `sddm.conf.d/` (dort steht `Session=Lubuntu`) → Installer ersetzt `/etc/sddm.conf`
  (Sicherung `…/sddm.conf.vor-vitrine`), Deinstallation stellt sie zurück
- Snap-Firefox braucht ein Home unter `/home` → Kiosk-Nutzer mit `/home/hydrahive-kiosk`, Login-Shell nötig (Sitzungsskript)
- Ein Neustart von sddm beendet alle Prozesse aus der alten Sitzung → die Brücke läuft **im Vitrine-Dienst**, nie in der Sitzung
- Abgebrochene Sitzungen bleiben als „closing“ hängen → `loginctl terminate-session` beim Rückbau
- Nie als root testen oder automatisch anmelden (am 18.10. kurz passiert, Lubuntu-Desktop als root sichtbar → sofort zurückgenommen)

## 1. `renderer/evdi_source.py` – Bild des virtuellen Monitors (eigener Code, Muster tinyscreen/MIT, siehe UPSTREAM.md)
- libevdi per ctypes (nur die nötigen Funktionen: check/add/open/connect/register/request_update/grab/handle_events/close)
- `EvdiSource.open(w, h)` → verbindet mit eigener EDID (`renderer/edid.py`, 1080×1920 bei 60 Hz), `next_jpeg()` → JPEG nur bei
  geändertem Inhalt (CRC), sonst `None`; `close()`
- fehlt libevdi oder das Modul → `EvdiUnavailable` (Dienst bleibt bei Video)
- Tests: EDID (Prüfsumme, 1080×1920, Name, Grenzen) wie `edid-decode` sie liest; Quelle mit gefälschter Bibliothek
  (unverändert → None, geändert → JPEG, Moduswechsel → Puffer neu)

## 2. `renderer/idle.py` – Leerlaufzeit des Kiosk-X-Servers
- libX11 + libXss per ctypes; Display `:0`, Xauthority aus der Kiosk-Sitzung (Pfad in `config.json`/Umgebung, nicht fest)
- `idle_ms()` → int oder `None` (kein X / keine Erlaubnis); Verbindung bleibt offen, neu verbinden bei Fehler
- Tests mit gefälschter Bibliothek: Werte, X weg → None, Wiederverbinden

## 3. `renderer/mode.py` – Entscheidung Video/Dashboard (reine Logik, ohne Geräte)
- Eingaben: Leerlauf (ms oder None), Dashboard verfügbar?, Rückkehrzeit, „Zurück“-Wunsch (Datei `<daten>/mode.json` vom Backend)
- Ausgabe: `video` | `dashboard`; Dashboard nur, wenn verfügbar; zurück nach Rückkehrzeit oder auf Wunsch;
  nach „Zurück“ erst wieder bei **neuer** Eingabe (Leerlauf kleiner als beim Zurückschalten)
- Tests: alle Übergänge, Grenzen der Rückkehrzeit, kein Flattern, Nachtmodus (Maus weckt, danach zurück zum Nachtbild)

## 4. Dienst (`renderer/main.py`)
- Je ¼ s `mode` prüfen; Moduswechsel gehört zum Programmschlüssel → `_Switch` wie heute
- `_play_dashboard`: Bilder aus `EvdiSource`, nur bei Änderung senden, höchstens 20/s; ohne Änderung alle 2 s das letzte Bild
  erneut (Display hält sonst nicht); Vorschau/state.json wie heute, `state.mode`
- EVDI/Idle nicht verfügbar → nie Dashboard, `state.dashboard = "nicht verfügbar: <Grund>"`
- main.py wird zu groß → Dashboard-Schleife in `renderer/play_dashboard.py`
- Tests: Wechsel Video → Dashboard → Video ohne Verbindungsverlust; EVDI-Fehler mitten im Dashboard → zurück zu Video, Fehler in state

## 5. Installation (`extension/install.sh` / `uninstall.sh`)
- Pakete: `linux-modules-evdi-generic libevdi1 openbox x11-xserver-utils` (Firefox ist auf .2 da; fehlt er → Hinweis, kein Abbruch)
- `/etc/modules-load.d/hydrahive2-vitrine-evdi.conf` + `modprobe.d` (`initial_device_count=1`)
- Nutzer `hydrahive-kiosk` (Home `/home/hydrahive-kiosk` wegen Snap, Passwort gesperrt, kein SSH per `DenyUsers`-Drop-in; Sitzung startet über sddm), Gruppen `video`,`input`
- Sitzung `/usr/share/xsessions/hydrahive-vitrine-kiosk.desktop` → Skript: Bildschirmschoner aus (`xset s off -dpms`), EVDI-Ausgang
  einschalten, Zugriff für den Dienst-Nutzer auf X (`xhost +SI:localuser:<dienst>`), Firefox `--kiosk` in Schleife
- Firefox-Richtlinie (`policies.json`): nur `127.0.0.1` erlaubt, keine Updates/Erstlauf-Seiten
- sddm: `/etc/sddm.conf` (hat Vorrang) mit Autologin Kiosk-Sitzung ersetzen; **vorher** sichern
- Dienst: `ReadWritePaths` unverändert; Zugriff auf `/tmp/.X11-unix` (PrivateTmp aus → nur `/tmp/.X11-unix` freigeben) und `/dev/dri/cardN` (Gruppe `video`)
- Deinstallation: Autologin-Datei entfernen (gesicherte zurück), Sitzung, Nutzer, Richtlinie, modules-load entfernen
- Prüfbar: Skript zweimal laufen lassen → gleiches Ergebnis (idempotent); `shellcheck`

## 6. Backend + Cockpit
- `POST /mode/video` („Zurück“) schreibt `<daten>/mode.json`; Platzhalter-Seite `GET /dashboard` (nur localhost, ohne Login in S1:
  statische Seite mit Uhr und Knopf „Zurück“, **keine Daten**)
- Cockpit: Statuskarte zeigt Modus und „Dashboard verfügbar / nicht verfügbar (Grund)“; Einstellung Rückkehrzeit (30 s – 30 min, Std. 2 min)
- Tests: Route nur von 127.0.0.1, Schema der Rückkehrzeit, Statusanzeige (vitest)

## 7. Abnahme am Gehäuse (mit Till)
- Trackpad bewegen → Dashboard < 1 s; 2 min nichts → Video; „Zurück“ → sofort; nachts weckt die Maus
- Neustart von .2: nie Anmeldebildschirm/Benutzername; Video < 90 s
- Last 60 s: Video < 10 %, Dashboard ruhig < 5 %, Dashboard bewegt < 20 % (Brücke + Firefox)
- Firefox beenden → Kiosk startet ihn neu; EVDI fehlt → Video läuft, Cockpit zeigt den Grund

Gegenprobe: Mutanten ohne Bytecode-Cache. Dateien ≤ 200 Zeilen. Version 0.7.0.

## Umsetzung (18.10.2026) – Abweichungen vom Plan, alle am Gerät begründet
- **EVDI im eigenen Thread** (`renderer/dashboard.py`): Ohne laufendes Abarbeiten der EVDI-Ereignisse hängt `xrandr` beim
  Einschalten des Ausgangs (am Gerät gesehen). Der Thread verarbeitet sie immer, Bilder holt er nur im Dashboard-Modus.
- **Mauszeiger** zeichnet Vitrine selbst (`renderer/cursor.py`): EVDI liefert den Bildschirminhalt ohne Zeiger.
  Position über `XQueryPointer` aus einer eigenen X-Verbindung (Xlib ist nicht threadsicher).
- **Kiosk-Zugang** über die Geräte-Routen des Kerns (`/api/module-device/vitrine/kiosk`, Rate-Limit) mit Kiosk-Schlüssel
  (`<daten>/kiosk.key`, 0600) **und** direkter Verbindung von 127.0.0.1 – statt einer eigenen Login-Ausnahme.
- **Kiosk nur ohne echten Monitor:** Der Installer richtet die Kiosk-Sitzung nicht ein, wenn ein Bildschirm angeschlossen ist
  (dann bleibt der Anmeldebildschirm), und auch nicht, wenn `<daten>/kiosk.off` existiert.
- **Update-sicherer Rückbau:** Ein Modul-Update ruft `uninstall.sh` + `install.sh`. Der Kiosk-Rückbau läuft daher
  verzögert (120 s) und nur, wenn das Modul danach wirklich fehlt; `install.sh` bricht ihn ab.
