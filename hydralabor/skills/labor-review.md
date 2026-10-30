---
name: labor-review
description: Prüfliste für Änderungen im Hydra-Labor, bevor sie als fertig gelten (Kurzfassung der HydraHive-Regeln).
when_to_use: Vor jeder Fertig-Meldung im Hydra-Labor und bevor eine Änderung eingereicht werden soll.
---

# Labor-Review

Gehe die Punkte der Reihe nach durch und nenne das Ergebnis jedes Punkts.

## 1. Tests zuerst

- Gibt es für die Änderung einen Test? War er vor dem Code rot und ist er jetzt grün?
- Kern: `cd /work/hydrahive2 && pytest -q -n 2 core/tests` – alles grün, nicht nur die neuen Tests.
- Modul: `cd /work/hydrahive2-modules/<modul> && pytest -q`.

## 2. Code-Prüfung

- `ruff check` auf die geänderten Python-Dateien: keine neuen Befunde.
- Frontend geändert: `cd /work/hydrahive2/frontend && npx tsc -b && npx vitest run`.

## 3. Aufbau

- Dateien höchstens etwa 200 Zeilen; sonst nach Themen aufteilen.
- Keine `print()`-Aufrufe im Server-Code, Logging verwenden.
- Pfade über die Einstellungen (`settings`), nicht fest im Code.
- Module importieren nicht voneinander.

## 4. Sicherheit

- Keine Passwörter, Tokens oder Schlüssel im Code, in Tests oder Beispieldateien.
- Neue Schnittstellen prüfen die Rechte (wer darf das?).
- Befehle nie über eine Shell mit Nutzereingaben zusammenbauen.

## 5. Ergebnis

Kurze Zusammenfassung: was geändert, welche Tests, was nicht getestet ist.
