# TV-Werkstatt – Bauplan Etappe E1 (Bauen und schieben)

Gehört zu `SPEC.md` (Task 42c78c45). Stand 13.11.2026: Entwurf, noch nichts gebaut.

## Ziel

Nach E1 gibt es das Modul `tvwerkstatt` 0.1.0: Ein Admin richtet per Klick die Bauumgebung ein, trägt einen Fernseher
ein, baut den Startbildschirm von cleanyourtv, installiert ihn und kann zum Original zurück. Alles Fremde läuft im
Container, das Netz des Containers ist gesperrt bis auf das Internet und Port 5555 der eingetragenen Fernseher.

## Dateien (je höchstens ca. 200 Zeilen)

- `manifest.json` – id `tvwerkstatt`, Freigabe `module.tvwerkstatt` admin_only, keine Agenten-Werkzeuge
- `migrations/001_tvwerkstatt.sql` – Geräte, Quellen, Bauten, Installiert, Aufträge
- `backend/__init__.py` – register: Migrationen, Router
- `backend/incus.py` – dünne Hülle um `hydrahive.containers.incus_client` (Muster vibe)
- `backend/network.py` – Netz `hhtvw0`, Sperrliste `hhtvw-acl`, Ausnahme je Fernseher, Probe aus dem Container
- `backend/container.py` – anlegen, starten, anhalten, Zustand
- `backend/provision.py` – Namensauflösung, Java, Android-Werkzeuge mit Prüfsumme, cleanyourtv am festen Commit, Python-venv
- `backend/source.py` – Quelle cleanyourtv: Commit festnageln, Prüfsumme des Gradle-Wrappers
- `backend/build.py` – Startbildschirm bauen, Protokoll, Prüfsumme, Gradle danach beenden, Container anhalten
- `backend/device.py` – Gerät eintragen, prüfen (`tv.py --probe` im Container), Debugging-Zustand
- `backend/install.py` – installieren, zurück zum Original, Ergebnis vom Gerät zurücklesen
- `backend/jobs.py` – Aufträge mit Schritt und Fehlercode (Muster vibe)
- `backend/state.py` – Zugriff auf die Tabellen
- `backend/routes.py` – Routen, nur Admins
- `frontend/` – Seite mit Reitern Desktop (E1: Bauen, Installieren, Zurück), Geräte, Bauumgebung; Texte de/en
- `tests/` – `fake_incus.py`, Tests je Baustein

## Bausteine (Reihenfolge, jeweils rote Tests zuerst)

### 1. Gerüst und Zugriff
- Tests: Manifest, Route ohne Admin → 403, Migration legt Tabellen an.
- Code: manifest, register, leere Routen, Zustand.

### 2. Netz und Sperrliste
- Tests: Sperrliste enthält alle privaten Bereiche und die eigenen Adressen des Servers; eine Fernseher-Adresse wird aus
  den gesperrten Bereichen herausgerechnet und nur für TCP 5555 erlaubt; Probe meldet offen/zu.
- Echte Messung auf dem Server (mit OK): aus dem Container Server :22/:443 und Router :80 zu, Fernseher :5555 offen,
  Fernseher :80 zu, Internet offen. Ergebnis hier eintragen.

### 3. Container und Einrichtung
- Tests: Anlegen mit festen Grenzen (unprivilegiert, kein Nesting, idmap isoliert), Namensauflösung wird gesetzt,
  Prüfsumme der cmdline-tools gegen Googles Verzeichnis, Abbruch bei Abweichung ohne Entpacken, Lizenz nur nach
  Bestätigung im Auftrag.
- Code: `container.py`, `provision.py`.

### 4. Quelle und Bau
- Tests: Commit festgenagelt, Wrapper-Prüfsumme gegen gradle.org, Bau-Fehler → `tvw_build_failed` mit Protokollende,
  Prüfsumme der App gespeichert, Container danach angehalten.
- Code: `source.py`, `build.py`, `jobs.py`.

### 5. Gerät
- Tests: Adresse nur im Heimnetz, Probe liest Modell/Android/SDK, `tvw_adb_unauthorized` bei fehlender Bestätigung,
  `tvw_sdk_too_old` unter SDK 26, Ausnahme in der Sperrliste wird beim Eintragen gesetzt und beim Löschen entfernt.
- Code: `device.py`.

### 6. Installieren und zurück
- Tests: Installation nur mit Rückfrage-Kennzeichen, Ergebnis vom Gerät zurückgelesen (Home-Eigentümer), Rückweg stellt
  den gespeicherten Original-Startbildschirm her, `tvw_home_not_switched` mit automatischem Rückweg.
- Code: `install.py`.

### 7. Debugging-Anzeige und Abschalten
- Tests: Zustand offen/zu aus der Probe, „ausschalten“ sendet nur den einen Befehl.
- Echte Messung (mit OK): Wirkt `settings put global adb_enabled 0` am Sony bis nach dem Neustart?

### 8. Oberfläche
- vitest für Zustände und Fehlertexte, Texte de/en mit gleichen Schlüsseln, Farben nur über Farbstufen des Kerns.

### 9. Abnahme am Sony (echt, mit Tills OK)
- Probe-Container von Hand vorher entfernen (Tills OK). Einrichten, Gerät eintragen, Bauen, Installieren, Zurück,
  wieder Installieren, Neustart, Debugging aus. Ergebnisse hier eintragen.

## Akzeptanzkriterien

Siehe `SPEC.md`, Abschnitt „Akzeptanzkriterien E1“.

## Nicht in E1

Aussehen (E2), Zusätze (E3), Entrümpeln (E4), eigene TV-App (E5), Agenten-Werkzeuge, mehrere Container.
