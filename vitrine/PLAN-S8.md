# Plan S8 — Licht (Spec: SPEC-LICHT.md)

Version 0.14.0. TDD: je Schritt erst rote Tests, dann Code, dann Mutantenprobe. Dateien ≤ 200 Zeilen.

| Datei | Inhalt | neu |
|---|---|---|
| `renderer/light_config.py` | Vorgaben, Prüfung, `normalize()` – eine Wahrheit für Dienst und Backend (wie dash_layout) | ja |
| `renderer/light_state.py` | Zustand wählen: Nacht, Fehler (blinkend/stehend), Wartet, Fertig, Arbeitet, Anlass, Jahreszeit | ja |
| `renderer/light_rgb.py` | OpenRGB aufrufen: feste Argumentliste, nur geprüfte Werte, Gerät suchen, Zeitlimit | ja |
| `renderer/light_runner.py` | Thread: alle 2 s Zustand, nur bei Änderung setzen, alle 10 min neu, Vorschau, Status-Datei | ja |
| `renderer/config.py` | `light` in DEFAULTS + load() | |
| `renderer/calendar.py` | `light_choice()` – passende Regel mit Lichtfarbe, auch ohne Video | |
| `renderer/calendar_templates.py` | Lichtfarben-Vorschläge in den Vorlagen | |
| `renderer/main.py` | `light_runner.start(data)` | |
| `backend/schemas.py` | `light` im Config-Schema (über light_config); Regelfelder `light_color`/`light_effect` | |
| `backend/light_routes.py` | `GET /light` (Status), `POST /light/preview` (Zustand, 15 s) | ja |
| `extension/install.sh` / `uninstall.sh` | openrgb nur bei `048d:5711`, udev-Regel 72-… für hidraw, Rückbau | |
| `frontend/LightCard.tsx` (+ `LightStateRow.tsx`) | Karte Beleuchtung | ja |
| `frontend/RuleFieldsExtra.tsx` | Lichtfarbe + Effekt je Regel | |
| `frontend/api.ts`, `index.tsx` | Typen, Texte de/en | |

## Schritte

1. **light_config** – Tests: Vorgaben; Farbe nur `^#?[0-9A-Fa-f]{6}$` → `RRGGBB`; Effekt ∈ static/breathing/flashing/off;
   Helligkeit/Tempo 0–100; Blinkzeit 0–600; Fertig-Dauer 2–60; Jahreszeiten vollständig; unbekannte Schlüssel weg;
   kaputte Werte → Vorgabe (Dienst), Schema lehnt ab (Backend).
2. **calendar.light_choice** – Tests: Regel ohne Video zählt; ohne Lichtfarbe zählt nicht; Priorität; aus = zählt nicht;
   Halloween 31.10. orange, 01.11. keine.
3. **light_state** – Tests: Reihenfolge (Nacht > Fehler > Wartet > Fertig > Arbeitet > Anlass > Jahreszeit); Fehler
   blinkend nur in den ersten N s ab Meldung, danach stehend; gelesen → weg; info ändert nichts; hydra.json alt →
   kein Arbeitet; Fertig nur beim Übergang >0 → 0 und nur für die Dauer; Licht aus → None; Nachts-aus abschaltbar;
   Jahreszeit-Farben aus → feste Ruhe-Farbe.
4. **light_rgb** – Tests (Fake-openrgb im PATH): Argumentliste exakt (`--noautoconnect --config <daten>/openrgb -d 0
   -m <mode> -c <RRGGBB> -b <n> [-s <n>]`); „aus“ = static 000000; nie shell; Zeitlimit; rc≠0/Gerät fehlt → Fehler;
   `find()` liest `-l`, nimmt das erste Motherboard.
5. **light_runner** – Tests: nur bei Änderung setzen; alle 10 min erneut; Vorschau 15 s überschreibt, danach zurück;
   Fehler zählen, Status-Datei `light.json` (Gerät, Zustand, Farbe, letzter Fehler); Ausnahme im Thread stoppt nichts;
   Gerät nicht gefunden → 5 min warten.
6. **Backend** – Schema `light` + Regelfelder; Routen Status/Vorschau (Recht module.vitrine, Zustand aus fester Liste).
7. **Installer** – Tests: openrgb nur, wenn `048d:5711` in lsusb und kein `light.off`; udev nur für 048d:5711 hidraw,
   Gruppe = Dienstnutzer; uninstall entfernt die Regel; `bash -n`.
8. **Oberfläche** – vitest: Karte zeigt Zustände, Prüfung im Browser wie Server; tsc, eslint, echter Build.
9. **Live auf .2** (nur .2, vorher Tills OK zum Update): Update, `light.json` zeigt Gerät; Zustände per Vorschau; echter
   Agentenlauf → blau; Testmeldung error → rot blinkend, Gelesen → zurück; Nacht-Zeitfenster kurz setzen → aus; Last.
10. **Abnahme durch Till** am Gehäuse.
