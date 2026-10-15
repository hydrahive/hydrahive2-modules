# Plan Vitrine E2 — Kalender, Nachtmodus, Cockpit-Seite

Spec: `vitrine/SPEC.md`. E1 läuft (Dienst, Video-Schleife, Uhr, Status).

## Grundidee
Eine **Konfigurationsdatei** `<daten>/config.json` ist die einzige Wahrheit. Das Backend schreibt sie (Cockpit),
der Dienst liest sie bei jeder Änderung neu (mtime, max. alle 5 s). Die Regel-Logik liegt in **einem**
Python-Modul (`renderer/calendar.py`), das Dienst *und* Backend benutzen — Vorschau im Cockpit = Verhalten am Display.

## config.json
```json
{
  "rules": [
    {"id": "…", "name": "Weihnachten", "kind": "range", "from": "12-24", "to": "12-26",
     "videos": ["weihnachten.mp4"], "priority": 50, "enabled": true},
    {"id": "…", "name": "Ostern", "kind": "easter", "offset_from": -2, "offset_to": 1, "videos": ["…"], "priority": 50},
    {"id": "…", "name": "Herbst", "kind": "season", "season": "autumn", "videos": ["herbst-hydra.mp4"], "priority": 10},
    {"id": "…", "name": "Abend", "kind": "time", "from": "18:00", "to": "23:00", "videos": ["…"], "priority": 20}
  ],
  "default_videos": [],
  "night": {"enabled": false, "from": "23:00", "to": "07:00", "mode": "dim"},
  "rotate_minutes": 10
}
```

## Regeln (`renderer/calendar.py`, rein, testbar)
- **Arten:** `range` (MM-TT bis MM-TT, auch über Jahreswechsel), `easter` (Tage relativ zu Ostersonntag, Gauß/Anonymous-Gregorian),
  `season` (meteorologisch: Frühling 03-01, Sommer 06-01, Herbst 09-01, Winter 12-01), `time` (HH:MM–HH:MM, auch über Mitternacht).
- **Wahl:** alle passenden + `enabled` + mindestens ein vorhandenes Video → höchste `priority` gewinnt; Gleichstand → alle
  Videos dieser Stufe zusammen. Keine Regel → `default_videos`, sonst alle Videos im Ordner, sonst Verlauf.
- **Wechsel:** mehrere Videos → alle `rotate_minutes` das nächste (nach Uhrzeit bestimmt, nicht zufällig — stabil nach Neustart).
- **Feiertagsname:** Regeln mit Art `range`/`easter` liefern ihren Namen fürs Overlay („Weihnachten“ unter dem Datum).
- **Fertige Vorlagen** (im Cockpit per Klick): Neujahr, Ostern, Pfingsten, Halloween, Advent (1. Advent bis 23.12.), Weihnachten, Silvester, 4 Jahreszeiten.

## Nachtmodus (`renderer/night.py`)
- `enabled`, `from`/`to` (über Mitternacht), `mode`: `dim` = schwarzes Bild mit gedimmter kleiner Uhr, `off` = schwarzes Bild.
- Im Nachtmodus: 1 Bild pro Sekunde statt 24 (spart CPU; Display bleibt verbunden).

## Dienst (`renderer/main.py`)
- liest `config.json` (mtime), fragt jede Sekunde `calendar.pick(now)`; ändert sich das Video → Wechsel mit kurzer Schwarzblende (0,5 s).
- Nachtmodus vor allem anderen.
- schreibt zusätzlich `preview.jpg` (alle 10 s, klein 270×480) für die Cockpit-Vorschau.

## Backend (`backend/`)
- `GET /status` (wie E1 + `rule`, `holiday`, `night`)
- `GET /config`, `PUT /config` (Pydantic-Validierung, atomar schreiben)
- `GET /videos`, `POST /videos` (Upload, ≤ 500 MB, Endung + `ffprobe`-Prüfung, Name säubern, kein Überschreiben), `DELETE /videos/{name}` (nur Dateiname, kein Pfad)
- `GET /preview.jpg`
- `GET /templates` (Vorlagen)
- `POST /simulate` (`{"at": "2026-12-24T19:00"}` → welche Regel/Video) — für die Vorschau „was läuft an Heiligabend?“
- alles hinter `module.vitrine` (Modul-Tor)

## Frontend (`frontend/`)
- Seite `/vitrine` im Cockpit (nav `working`), Dark-Cockpit-Stil wie Scratchpad/Mediaplayer
- **Kopf:** Status (läuft/verbunden/fps/aktuelles Video/Regel), Live-Vorschau (alle 10 s neu)
- **Videos:** Liste mit Größe/Dauer, Hochladen, Löschen (mit Rückfrage)
- **Kalender:** Regelliste (an/aus, Name, Zeitraum, Videos, Priorität), bearbeiten/neu/löschen, Vorlagen-Knöpfe, „Datum testen“
- **Einstellungen:** Nachtmodus (an/aus, von–bis, dim/aus), Wechselintervall
- i18n de/en

## Tests
- `calendar`: jede Art inkl. Jahreswechsel/Mitternacht, Ostern 2026 (05.04.) und 2027 (28.03.), Pfingsten = Ostern+49, Advent (1. Advent 2026 = 29.11.), Priorität, Gleichstand, fehlende Videos überspringen, Rotation stabil, Feiertagsname
- `night`: Fenster über Mitternacht, dim/off, aus
- `config`: Laden mit Defaults, kaputte Datei → Defaults (Dienst läuft weiter), Validierung im Backend (unbekannte Art, falsches Datum, fremde Videonamen → 422)
- Backend-Routen: Upload (Endung, Größe, ffprobe gemockt, Name-Säuberung, kein Pfad-Trick `../`), Löschen, simulate
- `main`: Videowechsel bei Regelwechsel, Nachtmodus 1 fps, Vorschau-Datei
- vitest: Formular-Helfer (Zeitraum-Text, Validierung im Browser)

Abnahme: am Gerät Datum simulieren (Weihnachten), Nachtmodus kurz aktivieren, Upload über die Seite.
