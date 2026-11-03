# Plan: Saisonale Nachtvideos

## Ziel

Die Vitrine kann im Nachtfenster saisonale Schlafvideos mit Uhr anzeigen. Acht wiederverwendbare Prompt-Rezepte bereiten die benötigten Clips vor.

## Dateien

- `backend/schemas.py` — `video`-Modus und validierte saisonale Pools.
- `renderer/config.py` — robuste Standardwerte und Migration alter Konfigurationen.
- `renderer/calendar.py` — gemeinsame Ermittlung der meteorologischen Saison.
- `renderer/program.py` — Auswahl, Rotation und `dim`-Fallback.
- `renderer/main.py` — Nachtvideo über normalen Decoder, ohne Status/Meldungskarten.
- `frontend/api.ts` — Typen für Modus und Pools.
- `frontend/SettingsCard.tsx` — dritter Nachtmodus und Einbindung der Pool-Auswahl.
- `frontend/NightVideoPools.tsx` — Videoauswahl je Jahreszeit.
- `frontend/index.tsx` — deutsche und englische Texte.
- `frontend/VitrinePage.tsx` — hochgeladene Videos an die Einstellungen reichen.
- `tests/test_config_night.py` — Defaults/Migration.
- `tests/test_program.py` — Saison, Rotation, fehlende Dateien, Fallback.
- `tests/test_main_program.py` — Videodecoder statt statischem Nachtbild, reduzierte Overlays.
- `tests/test_schemas*.py` bzw. neuer fokussierter Test — Backend-Validierung.
- `frontend/NightVideoPools.test.tsx` — sichtbare saisonale Auswahl.

## Implementierungsreihenfolge

### Task 1: Datenvertrag
- [ ] Backend- und Config-Tests für vier leere Pools, `video` und ungültige Namen schreiben.
- [ ] Tests rot ausführen.
- [ ] Schema und robuste Config-Normalisierung implementieren.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(vitrine): saisonale Nachtvideo-Konfiguration`

### Task 2: Programmauswahl
- [ ] Tests für alle vier Saisons, Rotation, Dateifilter und `dim`-Fallback schreiben.
- [ ] Tests rot ausführen.
- [ ] Saison-SSOT und Programmauswahl implementieren.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(vitrine): Nachtvideos saisonal auswählen`

### Task 3: Wiedergabe
- [ ] Diensttest für Nachtvideo-Decoder und reduzierte Overlays schreiben.
- [ ] Test rot ausführen.
- [ ] Wiedergabepfad für `night="video"` implementieren.
- [ ] Test grün ausführen.
- [ ] Commit: `feat(vitrine): Nachtvideos mit Uhr abspielen`

### Task 4: Cockpit
- [ ] Komponententest für vier Saison-Pools schreiben.
- [ ] Test rot ausführen.
- [ ] Typen, Moduswahl, Pool-Komponente und Übersetzungen implementieren.
- [ ] Vitest und TypeScript grün ausführen.
- [ ] Commit: `feat(vitrine): Nachtvideo-Pools im Cockpit verwalten`

### Task 5: Filmrezepte
- [ ] Acht Prompts aus dem freigegebenen Motivplan erstellen.
- [ ] Je Rezept 9:16, Start=Ende, tonlos und Uhr-Freiraum hinterlegen.
- [ ] Prompt-Archiv-Liste prüfen.

### Task 6: Gesamtprüfung
- [ ] Vollständige Vitrine-Pytest-Suite.
- [ ] Modul-Frontend TypeScript und Vitest.
- [ ] Ruff/Diff/Architektur-/Security-Review.
- [ ] PR erstellen und CI abwarten.

## Akzeptanzkriterien

- [ ] Saisonale Pools funktionieren und sind im Cockpit pflegbar.
- [ ] Fehlende Videos führen sicher zur gedimmten Uhr.
- [ ] Bestehende `dim`-/`off`-Konfigurationen bleiben kompatibel.
- [ ] Nachtvideo zeigt Uhr/Datum ohne Status/Meldungskarten.
- [ ] Acht Prompt-Rezepte sind verfügbar.

## Nicht in diesem Plan

- Automatisches Rendern der Videos durch den Agenten.
- Upload nicht abgenommener Clips auf die Vitrine.
- Änderung des generellen Kalenderregel-Systems.
- Eigene Rotationszeit nur für Nachtvideos; zunächst gilt `rotate_minutes` gemeinsam.
